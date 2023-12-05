from typing import List, Optional, Tuple, Union

from ninja import Field, ModelSchema, Router, Schema
from ninja.orm import create_schema

from django.db import utils
from django.shortcuts import get_list_or_404, get_object_or_404

from tree.models import Tree, TreeKind, Version
from .models import Decision, ExpertRequest, RequestData
from .evaluator import Evaluator


router = Router(tags=["decision"])


class RequestDataIn(Schema):
    data_type: int
    data_value: Union[int, str, bool, List[Union[int, str, bool]]]


class ExpertRequestIn(ModelSchema):
    data: List[RequestDataIn] = Field(None)

    class Meta:
        model = ExpertRequest
        fields = ["identifier", "sec_identifier"]
        # at some point we need the version or the kind of tree here


class CriteriaOut(Schema):
    id: str
    input_value: Union[bool, int, str, list]
    result: bool
    based_on: str


class FullCriteriaOut(Schema):
    id: str
    number: int
    name: str
    description: str
    color: int
    data_type: int
    comparison_value: Union[int, bool, str]
    comparison_method: str
    list_comparison_method: str
    explanation: str
    input_value: Union[bool, int, str, list]
    result: bool
    based_on: str


class DecisionOut(Schema):
    identifier: str
    sec_identifier: str
    version: str
    is_preliminary: bool  # True wenn request fehlerhaft
    description: str  # Fehlercode + Beschreibung oder Ergebnis
    result: Optional[bool] = None
    leaf_id: Optional[str] = None
    missing_data: Optional[int] = None  # nur falls Daten fehlen
    node_missing_sth: Optional[str] = None  # nur falls Daten fehlen


class FullResultOut(Schema):
    decision: DecisionOut
    criteria: List[FullCriteriaOut] = []


class ShortResultOut(Schema):
    decision: DecisionOut
    criteria: List[CriteriaOut] = []


# === utility functions for decision making =================================
def get_version(kind_of_tree_id: int = None) -> Version:
    """
    if given a tree kind id, this returns the current version for this tree kind
    else it returns the current version of the first tree kind in the database
    """
    if kind_of_tree_id:
        return Version.objects.get_current_version(
            kind_of_tree=TreeKind.objects.get(id=kind_of_tree_id)
        )
    return Version.objects.get_current_version(kind_of_tree=TreeKind.objects.first())


def save_request_data(
    expert_request: ExpertRequestIn, kind_id: int = None
) -> Tuple[ExpertRequest, List[RequestData]]:
    """
    input: a single expert request with input data
    split the data and identification and save both for later analysis
    output: the request information that was saved and the saved data
    """
    version = get_version(kind_id)
    saved_request = ExpertRequest.objects.create(
        identifier=expert_request.identifier,
        sec_identifier=expert_request.sec_identifier,
        version=version,
    )
    # split saved request data for evaluation
    saved_data = []
    for data in expert_request.data:
        try:
            saving = RequestData.objects.create(
                request=saved_request, type_id=data.data_type, value=data.data_value
            )
            saved_data.append(saving)
        except utils.IntegrityError:
            # do not save data with strange data type identifiers to prevent
            # IntegrityError
            pass
    return saved_request, saved_data


def get_evaluator_for_version(version: Version) -> Evaluator:
    """
    look for current complete tree and build an evaluator with it
    output: evaluator ready to run
    """
    # get tree
    tree = Tree.objects.get_complete_tree(version)
    # build evaluator
    return Evaluator(tree=tree[0], nodes=tree[1], leafs=tree[2])


def get_decision(
    evaluator: Evaluator,
    request_data_list: List[RequestData],
    expert_request: ExpertRequest,
) -> Tuple[DecisionOut, FullCriteriaOut]:
    """
    input:
        evaluator: runnable evaluator with current tree
        request_data_list: all of the data that is available about this entity
        expert_request: information about the entity to identify it by
    output:
        decision: either with the completed result of the tree or information about
                    about the missing data types
        criteria: all the nodes that were visited while running through the tree
    run evaluator through tree and save the response
    """
    # run a data set through tree and record criteria
    evaluator.run_tree(data=request_data_list)
    # was the evaluation successful or is data missing?
    if evaluator.missing_data is not None:
        # save the partial way through the tree
        result = (
            "missing data to evaluate tree: "
            + evaluator.missing_data.display_name
            + " ("
            + str(evaluator.missing_data.id)
            + ") at node with id:"
            + str(evaluator.node_missing_sth.id)
        )
        Decision.objects.create(
            request=expert_request,
            description=result,
            is_preliminary=True,
        )
        # return full information
        return (
            DecisionOut(
                identifier=expert_request.identifier,
                sec_identifier=expert_request.sec_identifier,
                version=str(expert_request.version),
                is_preliminary=True,
                description=result,
                missing_data=evaluator.missing_data.id,
                node_missing_sth=evaluator.node_missing_sth.id,
            ),
            evaluator.criteria,
        )
    else:
        # save decision
        Decision.objects.create(
            request=expert_request,
            description=evaluator.end_leaf.display_name,
            result=evaluator.end_leaf.result,
            end_leaf=evaluator.end_leaf,
            is_preliminary=False,
        )
        return (
            DecisionOut(
                identifier=expert_request.identifier,
                sec_identifier=expert_request.sec_identifier,
                version=str(expert_request.version),
                is_preliminary=False,
                description=evaluator.end_leaf.display_name,
                result=evaluator.end_leaf.result,
                leaf_id=evaluator.end_leaf.id,
                node_missing_sth=None,
                missing_data=None,
            ),
            evaluator.criteria,
        )


# === /bunch === get decisions for a bunch of entities =======================
@router.post(
    "/bunch/{fullresult}",
    response={200: List[Union[FullResultOut, ShortResultOut]]},
    exclude_unset=True,
    exclude_none=True,
)
def decision_bunch(
    request, data: List[ExpertRequestIn], fullresult: bool, kind_id: int = None
):
    """
    Get recommendations for a number of entities. If no **tree kind** id is provided,
    the default tree (inital, id=1) is chosen.
    See **/decision/{fullresult}** for the required structure of the request data and
    the returned recommendation. {fullresult} is not available for this endpoint, since
    it would bloat the response in total. If you need **explanations**, please use the
    endpoint /tree/explanation and the ids provided in the recommendation to
    construct it.
    """
    # if no tree_kind is supplied, the default tree (id 1) is used
    # save request list
    print(data[0].identifier)
    saved_requests = []
    saved_requests_data = []
    for expert_request in data:
        saved_request, saved_request_data = save_request_data(expert_request, kind_id)
        saved_requests.append(saved_request)
        saved_requests_data.append(saved_request_data)
    # get tree and evaluator
    evaluator = get_evaluator_for_version(saved_requests[0].version)

    # save decisions for individual requests in a response list
    response_list = []
    for saved_request_data, saved_request in zip(saved_requests_data, saved_requests):
        decision, criteria = get_decision(evaluator, saved_request_data, saved_request)
        if fullresult:
            response_list.append(FullResultOut(decision=decision, criteria=criteria))
        else:
            response_list.append(ShortResultOut(decision=decision, criteria=criteria))

    return 200, response_list


DecisionLogOut = create_schema(
    Decision,
    name="DecisionLogOut",
    depth=1,
    fields=["id", "request", "description", "result", "end_leaf", "is_preliminary"],
)


# === /result/request_id === get logged decision for a request ========================
@router.get("/result/{int:request_id}", response={200: DecisionLogOut, 404: str})
def decision_for_request(request, request_id: int):
    """
    Retrieves the saved decision/recommendation for a previously made request.
    If you don't know your request id, get it using the endpoint
    /decision/requests/{identifier}/{secIdentifier} and choose the request that matches
    your time frame.
    """
    return get_object_or_404(Decision, request__id=request_id)


class ExpertRequestOut(ModelSchema):
    class Meta:
        model = ExpertRequest
        fields = ["id", "date", "identifier", "sec_identifier", "version"]


# === /requests/identifier/sec_identifier === retrieve all requests that were made for a
# specific entity identified by the identifier and second identifier
@router.get(
    "/requests/{str:identifier}/{str:secIdentifier}",
    response={200: List[ExpertRequestOut], 404: str},
)
def requests_for_entity(request, identifier: str, secIdentifier: str):
    """
    Return all requests that are associated with this entity specified by the
    identifier and second identifier as a list.
    This includes the date the request was made and the version id of the tree that
    was used.

    To then get the decision/recommendation that was made use the endpoint
    /decision/result/{request_id}. To see the data that was given in this request use
    /decision/data/{request_id}.
    """
    return get_list_or_404(
        ExpertRequest, identifier=identifier, sec_identifier=secIdentifier
    )


class RequestDataOut(ModelSchema):
    class Meta:
        model = RequestData
        fields = ["id", "type", "value"]


# === /data/request_id === retrieve all data from a specific request
@router.get("/data/{int:request_id}", response={200: List[RequestDataOut], 418: str})
def input_data_for_request(request, request_id: int):
    """
    Returns the input data that was given for a specific request as a list.
    The data objects consist of:
    * **id**: the primary key to save this data object in the database.
    * **type**: the id of the datatype that this data object belongs to.
    * **value**: the value that was given, this can be an int, boolean or string
    """
    return get_list_or_404(RequestData, request__id=request_id)


# === /fullresult === get decision for one entity ============================
@router.post(
    "/{fullresult}",
    response={200: Union[FullResultOut, ShortResultOut], 400: str, 500: str},
    exclude_unset=True,
    exclude_none=True,
)
def decision_one_entity(
    request, expert_request: ExpertRequestIn, fullresult: bool, kind_id: int = None
) -> DecisionOut:
    """
    Get a recommendation for one entity. If no tree kind is provided, the default
    tree (initial, id=1) is used.
    The input should be include the following values:
    * **identifier**: unique id of this entity
    * **sec_identifier**: another unique id for the entity to be identified with
    (both used to identify the entity later)
    * **data**: a list of datatype and value pairs with the input data
    To formulate the data list correctly check out the available datatypes under
    /core/datatype/all. Use the id of the datatype of this value to create pairs
    of datatype ids and values.

    The result that this endpoint either returns a full or a short result depending
    on the {fullresult} parameter that was received. Both are structured similarly:
    * **decision**: the recommendation with the basic information (identifier,
    sec_identifier, ...)
    * **criteria**: the path through the decision tree (in a short or full version)

    The **decision** summarizes the basic information about the entity, the used tree
    and the recommendation:
    * **identifier**: same as in input
    * **sec_identifier**: same as in input
    * **version**: version of the tree that was used (e.g. "Testbaum: 1.2")
    * **is_preliminary**: did the decision tree run until it has reached a leaf
    (-> false) or until some data was missing (-> true)?
    * **description**: if is_preliminary is false, this specifies the name of the leaf. if
    the result is preliminary, this tells you where and which datatype is missing.
    * **result**: if your tree offers a binary decision in the end, this is where you
    will find the result.
    * **leaf_id**: the id of the result leaf
    * **missing_data**: the id of the datatype that is missing
    * **node_missing_sth**: the node where this datatype is missing

    The **criteria list** includes all nodes that the entity passed on its way through
    the decision tree. Each node object consists of:
    * **id**: the node id (e.g. "1_1.2_N.1" -> kind of tree + version + N(ode) + number)
    * **input_value**: the data value(s) that was compared to the node value
    * **result**: the result of the comparison
    * **based_on**: the next node (think of going the path from the bottom of the tree
    starting with the leaf that's the result)
    If the request specified fullresult=true, the criteria node objects will also
    include:
    * **number**: the node number, used to specify connections between nodes and leaves
    when the tree is fed into the system through /tree/new
    * **name**: the short name of this node
    * **description**: the longer name of this node
    * **color**: the color id of this criterion (see /tree/colors)
    * **datatype**: id of the datatype that is compared in this node
    * **comparison_value**: the value of the node that the input is compared to
    * **comparison_method**: the comparison method (see /tree/new for more detail)
    * **list_comparison_method**: how to compare if more than one value is given as
    input
    * **explanation**: the explanation for this node and the successor
    """
    # if no tree_kind_id is supplied, the default tree (id 1) is used
    # save request
    saved_request, saved_request_data = save_request_data(expert_request, kind_id)
    # build tree and get evaluator
    evaluator = get_evaluator_for_version(version=saved_request.version)
    # evaluate data given the tree and return decision response
    decision, criteria = get_decision(evaluator, saved_request_data, saved_request)
    if fullresult:
        return 200, FullResultOut(decision=decision, criteria=criteria)
    else:
        return 200, ShortResultOut(decision=decision, criteria=criteria)
