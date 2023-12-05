# Copyright (c) 2022, DFKI GmbH - all rights reserved

import json
import os
from unittest.mock import call, patch

from django.test import Client, TestCase

from core.models import DataType
from tree.models import Tree, TreeKind, TreeLeaf, TreeNode, Version

from ..api import (
    RequestDataIn,
    ExpertRequestIn,
    get_decision,
    get_evaluator_for_version,
    save_request_data,
)
from ..models import RequestData, ExpertRequest, Decision


class DecisionApiTests(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.tree_kind = TreeKind(name="Test Kind", description="test description")
        cls.tree_kind.save()
        cls.version = Version(kind_of_tree=cls.tree_kind, major=0, minor=1)
        cls.version.save()
        cls.first_leaf = TreeLeaf(
            tree_version=cls.version,
            number=1,
            display_name="test_result1",
            result=False,
        )
        cls.first_leaf.save()
        cls.second_leaf = TreeLeaf(
            tree_version=cls.version,
            number=2,
            display_name="test_result2",
            result=True,
        )
        cls.second_leaf.save()
        cls.data_type = DataType(name="TEST1", display_name="test type")
        cls.data_type.save()
        cls.node = TreeNode(
            tree_version=cls.version,
            number=4,
            display_name="test_node",
            description="this is a description",
            data_type=cls.data_type,
            data_value=700000,
            explanation="explain this",
            true_successor=cls.first_leaf,
            false_successor=cls.second_leaf,
        )
        cls.node.save()
        cls.boolean_node = TreeNode(
            tree_version=cls.version,
            number=10,
            display_name="boolean_test_node",
            description="this is a boolean test node",
            data_type=cls.data_type,
            data_value=True,
            comparison=TreeNode.EQUAL,
            explanation="no explanation for this",
            true_successor=cls.first_leaf,
            false_successor=cls.second_leaf,
        )
        cls.boolean_node.save()
        cls.tree = Tree(root=cls.node, tree_version=cls.version)
        cls.tree.save()
        cls.client = Client()

    @patch("decision.evaluator.Evaluator")
    @patch("tree.models.Tree.objects.get_complete_tree")
    def test_use_tree_get_current_tree(self, mock_tree, MockEvaluator):
        # arrange
        mock_tree.return_value = [
            self.tree,
            [self.node],
            [self.first_leaf, self.second_leaf],
        ]
        # act
        get_evaluator_for_version(version=self.version)
        # assert
        assert MockEvaluator.called_with(
            tree=self.tree,
            nodes=[self.node],
            leafs=[self.first_leaf, self.second_leaf],
        )
        assert mock_tree.called

    @patch("decision.evaluator.Evaluator", autospec=True)
    def test_get_decision_call_run_tree(self, MockEvaluator):
        # arrange
        mock_evaluator = MockEvaluator(
            tree=self.tree, nodes=[self.node], leafs=[self.first_leaf, self.second_leaf]
        )
        mock_evaluator.missing_data = self.data_type
        mock_evaluator.node_missing_sth = self.node
        mock_evaluator.criteria = []
        request = ExpertRequest(
            identifier="test_entity",
            sec_identifier="test_entity_info",
            version=self.version,
        )
        request.save()
        data = RequestData(request=request, type=self.data_type, value="1")
        data.save()
        # act
        get_decision(
            evaluator=mock_evaluator,
            request_data_list=[data],
            expert_request=request,
        )
        # assert
        mock_evaluator.run_tree.assert_called_once_with(data=[data])

    @patch("decision.evaluator.Evaluator", autospec=True)
    def test_get_decision_return_decisionout_for_complete(self, MockEvaluator):
        # arrange
        mock_evaluator = MockEvaluator(
            tree=self.tree, nodes=[self.node], leafs=[self.first_leaf, self.second_leaf]
        )
        mock_evaluator.missing_data = None
        mock_evaluator.criteria = []
        mock_evaluator.end_leaf = self.second_leaf
        request = ExpertRequest(
            identifier="test_entity",
            sec_identifier="test_entity_info",
            version=self.version,
        )
        request.save()
        data = RequestData(request=request, type=self.data_type, value="1")
        data.save()
        # act
        decision, criteria = get_decision(
            evaluator=mock_evaluator,
            request_data_list=[data],
            expert_request=request,
        )
        # assert
        self.assertEqual(decision.identifier, request.identifier)
        self.assertEqual(decision.sec_identifier, request.sec_identifier)
        self.assertFalse(decision.is_preliminary)
        self.assertEqual(decision.description, self.second_leaf.display_name),
        self.assertEqual(decision.result, self.second_leaf.result)
        self.assertEqual(decision.leaf_id, self.second_leaf.id)
        self.assertEqual(criteria, [])

    @patch("decision.evaluator.Evaluator", autospec=True)
    def test_get_decision_return_decisionout_for_missing(self, MockEvaluator):
        # arrange
        mock_evaluator = MockEvaluator(
            tree=self.tree, nodes=[self.node], leafs=[self.first_leaf, self.second_leaf]
        )
        mock_evaluator.missing_data = self.data_type
        mock_evaluator.criteria = []
        mock_evaluator.node_missing_sth = self.node
        request = ExpertRequest(
            identifier="test_entity",
            sec_identifier="test_entity_info",
            version=self.version,
        )
        request.save()
        data = RequestData(request=request, type=self.data_type, value="1")
        data.save()
        # act
        decision, criteria = get_decision(
            evaluator=mock_evaluator,
            request_data_list=[data],
            expert_request=request,
        )
        # assert
        self.assertEqual(decision.identifier, request.identifier)
        self.assertEqual(decision.sec_identifier, request.sec_identifier)
        self.assertTrue(decision.is_preliminary)
        self.assertEqual(type(decision.description), str),
        self.assertEqual(decision.missing_data, self.data_type.id)
        self.assertEqual(decision.node_missing_sth, self.node.id)
        self.assertEqual(criteria, [])

    @patch("decision.evaluator.Evaluator", autospec=True)
    @patch("decision.models.Decision.objects")
    def test_get_decision_create_decision_for_missing(
        self, mock_decision_create, MockEvaluator
    ):
        # arrange
        mock_evaluator = MockEvaluator(
            tree=self.tree, nodes=[self.node], leafs=[self.first_leaf, self.second_leaf]
        )
        mock_evaluator.missing_data = self.data_type
        mock_evaluator.criteria = []
        mock_evaluator.node_missing_sth = self.node
        mock_decision_create.create.return_value = True
        request = ExpertRequest(
            identifier="test_entity",
            sec_identifier="test_entity_info",
            version=self.version,
        )
        request.save()
        data = RequestData(request=request, type=self.data_type, value="1")
        data.save()
        # act
        get_decision(
            evaluator=mock_evaluator,
            request_data_list=[data],
            expert_request=request,
        )
        # assert
        assert mock_decision_create.create.called

    @patch("decision.evaluator.Evaluator", autospec=True)
    @patch("decision.models.Decision.objects")
    def test_get_decision_create_decision_for_complete(
        self, mock_decision_create, MockEvaluator
    ):
        # arrange
        mock_evaluator = MockEvaluator(
            tree=self.tree, nodes=[self.node], leafs=[self.first_leaf, self.second_leaf]
        )
        mock_evaluator.missing_data = None
        mock_evaluator.criteria = []
        mock_evaluator.end_leaf = self.second_leaf
        mock_decision_create.create.return_value = True
        request = ExpertRequest(
            identifier="test_entity",
            sec_identifier="test_entity_info",
            version=self.version,
        )
        request.save()
        data = RequestData(request=request, type=self.data_type, value="1")
        data.save()
        # act
        get_decision(
            evaluator=mock_evaluator,
            request_data_list=[data],
            expert_request=request,
        )
        # assert
        mock_decision_create.create.assert_called_with(
            request=request,
            description=self.second_leaf.display_name,
            result=self.second_leaf.result,
            end_leaf=self.second_leaf,
            is_preliminary=False,
        )

    @patch("decision.api.get_version")
    @patch("decision.models.ExpertRequest.objects")
    def test_save_request_data_create_request(
        self, mock_expert_request, mock_get_version
    ):
        # arrange
        request = ExpertRequestIn(
            identifier="test_entity", sec_identifier="test_entity_info", data=[]
        )
        mock_expert_request.create.return_value = "test"
        mock_get_version.return_value = "test_version"
        # act
        result = save_request_data(expert_request=request)
        # assert
        self.assertEqual(result[0], "test")
        mock_expert_request.create.assert_called_with(
            identifier="test_entity",
            sec_identifier="test_entity_info",
            version="test_version",
        )

    @patch("decision.models.RequestData.objects")
    @patch("decision.models.ExpertRequest.objects")
    def test_save_request_data_create_data(
        self, mock_expert_request, mock_request_data
    ):
        # arrange
        request = ExpertRequestIn(
            identifier="test_entity",
            sec_identifier="test_entity_info",
            data=[
                RequestDataIn(data_type=self.data_type.id, data_value=5),
                RequestDataIn(data_type=self.data_type.id, data_value=True),
                RequestDataIn(data_type=self.data_type.id, data_value="test"),
            ],
        )
        mock_expert_request.create.return_value = "request"
        mock_request_data.create.return_value = "test"
        expected_calls = [
            call(request="request", type_id=self.data_type.id, value=5),
            call(request="request", type_id=self.data_type.id, value=True),
            call(request="request", type_id=self.data_type.id, value="test"),
        ]
        # act
        result = save_request_data(expert_request=request)
        # assert
        self.assertEqual(result[1], ["test", "test", "test"])
        mock_request_data.create.assert_has_calls(expected_calls)

    def test_client_get_request_for_entity_none(self):
        # arrange
        # act
        response = self.client.get(
            "/api/decision/requests/test_entity/test_entity_info"
        )
        # assert
        self.assertEqual(response.status_code, 404)

    def test_client_get_requests_for_entity(self):
        # arrange
        request = ExpertRequest(
            identifier="test_entity",
            sec_identifier="test_entity_info",
            version=self.version,
        )
        request.save()
        # act
        response = self.client.get(
            "/api/decision/requests/test_entity/test_entity_info"
        )
        # assert
        request_out = response.json()[0]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(request_out["id"], request.id)
        self.assertEqual(request_out["identifier"], "test_entity")
        self.assertEqual(request_out["sec_identifier"], "test_entity_info")
        self.assertIsNotNone(request_out["date"])

    def test_client_get_data_for_request(self):
        # arrange
        request = ExpertRequest(
            identifier="test_entity",
            sec_identifier="test_entity_info",
            version=self.version,
        )
        request.save()
        data = RequestData(request=request, type=self.data_type, value="42")
        data.save()
        # act
        response = self.client.get("/api/decision/data/" + str(request.id))
        # assert
        data_out = response.json()[0]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data_out["id"], data.id)
        self.assertEqual(data_out["type"], self.data_type.id)
        self.assertEqual(data_out["value"], "42")

    def test_client_get_decision_for_request(self):
        # arrange
        request = ExpertRequest(
            identifier="test_entity",
            sec_identifier="test_entity_info",
            version=self.version,
        )
        request.save()
        decision = Decision(
            request=request,
            description="test_result",
            result=self.first_leaf.result,
            end_leaf=self.first_leaf,
            is_preliminary=False,
        )
        decision.save()
        # act
        response = self.client.get("/api/decision/result/" + str(request.id))
        # assert
        result = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(result["id"], decision.id)
        self.assertEqual(result["request"]["id"], request.id)
        self.assertEqual(result["description"], "test_result")
        self.assertEqual(result["result"], self.first_leaf.result)
        self.assertEqual(result["end_leaf"]["id"], self.first_leaf.id)
        self.assertFalse(result["is_preliminary"])


def helper_replace_datatype_str_with_ids(json, datatype_dict):
    for key in json:
        for element in json[key]["data"]:
            element["data_type"] = datatype_dict[element["data_type"]]
    return json


def helper_replace_datatype_str_with_ids_in_tree(json, datatype_dict):
    for node in json["nodes"]:
        node["data_type_id"] = datatype_dict[node["data_type_id"]]
    return json


def helper_add_treekindid_to_ids(json, treekindid):
    tkid_str = str(treekindid)
    for testcase in json.values():
        # decision part
        testcase["decision"]["leaf_id"] = (
            tkid_str + "_" + testcase["decision"]["leaf_id"]
        )
        # criteria part
        for criteria in testcase["criteria"]:
            criteria["id"] = tkid_str + "_" + criteria["id"]
            if criteria["based_on"] != "":
                criteria["based_on"] = tkid_str + "_" + criteria["based_on"]
    return json


class DecisionIntegrationTests(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        # setup client for get and post requests
        cls.client = Client()

        # setup tree and data types
        file_core = open(os.path.join(os.path.dirname(__file__), "testinput_core.json"))
        file_tree = open(os.path.join(os.path.dirname(__file__), "testinput_tree.json"))
        file_kind = open(os.path.join(os.path.dirname(__file__), "testinput_kind.json"))
        data_core = json.load(file_core)
        data_tree = json.load(file_tree)
        data_kind = json.load(file_kind)
        file_core.close()
        file_tree.close()
        file_kind.close()

        # add tree kind to data base
        response = cls.client.post("/api/tree/kind/new", data_kind, "application/json")
        print(response.json())
        cls.tree_kind_id = response.json()["id"]

        # read data types
        for data_type in data_core:
            response = cls.client.post(
                "/api/core/datatype/new", data_type, "application/json"
            )
            print(response.json())

        # build dict of datatype to use later to have the right ids
        cls.datatype_dict = dict()
        for datatype in DataType.objects.all():
            cls.datatype_dict[datatype.name] = datatype.id

        # switch data type strings out for the ids in tree
        data_tree = helper_replace_datatype_str_with_ids_in_tree(
            data_tree, cls.datatype_dict
        )

        # read tree and hope the data type ids match up ...
        response = cls.client.post(
            "/api/tree/new/" + str(cls.tree_kind_id), data_tree, "application/json"
        )
        print(response.json())

        # setup decision inputs and outputs
        file_input = open(
            os.path.join(os.path.dirname(__file__), "testinput_decision.json")
        )
        file_output = open(
            os.path.join(os.path.dirname(__file__), "testoutput_decision.json")
        )
        cls.decision_input = helper_replace_datatype_str_with_ids(
            json.load(file_input), cls.datatype_dict
        )
        cls.decision_output = helper_add_treekindid_to_ids(
            json.load(file_output), cls.tree_kind_id
        )

        file_input.close()
        file_output.close()

    def test_simple_input(self):
        # arrange
        input = self.decision_input["1-1.0_L.20"]
        output = self.decision_output["1-1.0_L.20"]["decision"]
        # act
        response = self.client.post("/api/decision/false", input, "application/json")
        data = response.json()
        # assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["decision"]["result"], output["result"])
        self.assertEqual(data["decision"]["identifier"], input["identifier"])
        self.assertEqual(data["decision"]["is_preliminary"], output["is_preliminary"])
        self.assertEqual(data["decision"]["description"], output["description"])
        self.assertEqual(data["decision"]["leaf_id"], output["leaf_id"])
        self.assertEqual(data["decision"].get("missing_data"), None)
        self.assertEqual(data["decision"].get("node_missing_sth"), None)
        self.assertEqual(
            data["criteria"], self.decision_output["1-1.0_L.20"]["criteria"]
        )
        self.assertEqual(data, self.decision_output["1-1.0_L.20"])

    def test_simple_input_bunch(self):
        # arrange
        input = self.decision_input["1-1.0_L.20"]
        # act
        response = self.client.post(
            "/api/decision/bunch/false", [input], "application/json"
        )
        # assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0], self.decision_output["1-1.0_L.20"])

    def test_simple_bunch_yields_same_as_single(self):
        # arrange
        input = self.decision_input["1-1.0_L.20"]
        # act
        response_single = self.client.post(
            "/api/decision/false", input, "application/json"
        )
        response_bunch = self.client.post(
            "/api/decision/bunch/false", [input], "application/json"
        )
        # assert
        self.assertEqual(response_single.json(), response_bunch.json()[0])

    def test_results_for_all_paths_through_tree(self):
        # arrange
        self.maxDiff = None

        # act
        for key in self.decision_input:
            # act
            print(key)
            response = self.client.post(
                "/api/decision/false", self.decision_input[key], "application/json"
            )
            # assert
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), self.decision_output[key])


class DecisionLongTests(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        # setup client for get and post requests
        cls.client = Client()

        # setup tree and data types
        file_core = open(os.path.join(os.path.dirname(__file__), "testinput_core.json"))
        file_tree = open(os.path.join(os.path.dirname(__file__), "test_long_tree.json"))
        file_kind = open(os.path.join(os.path.dirname(__file__), "testinput_kind.json"))
        data_core = json.load(file_core)
        data_tree = json.load(file_tree)
        data_kind = json.load(file_kind)
        file_core.close()
        file_tree.close()
        file_kind.close()

        # add tree kind to data base
        response = cls.client.post("/api/tree/kind/new", data_kind, "application/json")
        cls.tree_kind_id = response.json()["id"]

        # read data types
        for data_type in data_core:
            response = cls.client.post(
                "/api/core/datatype/new", data_type, "application/json"
            )

        # build dict of datatype to use later to have the right ids
        cls.datatype_dict = dict()
        for datatype in DataType.objects.all():
            cls.datatype_dict[datatype.name] = datatype.id

        # switch data type strings out for the ids in tree
        data_tree = helper_replace_datatype_str_with_ids_in_tree(
            data_tree, cls.datatype_dict
        )

        # read tree and hope the data type ids match up ...
        response = cls.client.post(
            "/api/tree/new/" + str(cls.tree_kind_id), data_tree, "application/json"
        )

        # setup decision inputs and outputs
        file_input = open(os.path.join(os.path.dirname(__file__), "test_long_in.json"))
        file_output = open(
            os.path.join(os.path.dirname(__file__), "test_long_out.json")
        )
        cls.long_input = helper_replace_datatype_str_with_ids(
            json.load(file_input), cls.datatype_dict
        )
        cls.long_output = json.load(file_output)

        file_input.close()
        file_output.close()

    def test_input(self):
        # arrange
        PACK_SIZE = 100
        outs = 0
        count = 0
        package = []
        for key in self.long_input:
            package.append(key)

            # package full or are we at end of input?
            if len(package) == PACK_SIZE or count == len(self.long_input) - 1:
                if count % 1000 == 0:
                    print(count)
                post_input = [self.long_input[entity] for entity in package]
                response = self.client.post(
                    "/api/decision/bunch/false", post_input, "application/json"
                )

                response_json = response.json()
                # assert
                self.assertEqual(response.status_code, 200)

                for num in range(0, len(post_input)):
                    input_one = post_input[num]
                    output_one = response_json[num]["decision"]
                    result = self.long_output[input_one["identifier"]]["decision"]
                    self.assertEqual(output_one["identifier"], result["identifier"])
                    self.assertEqual(
                        output_one["sec_identifier"], result["sec_identifier"]
                    )
                    if output_one["is_preliminary"] != result["is_preliminary"]:
                        print(self.long_input[input_one["identifier"]])
                        print(result)
                        print(response_json[num])
                        print(input_one["identifier"])
                    self.assertEqual(
                        output_one["is_preliminary"], result["is_preliminary"]
                    )
                    if output_one["is_preliminary"]:
                        assert output_one["description"].startswith(
                            result["description"]
                        )
                    else:
                        if output_one["result"] != result["result"]:
                            print(input_one)
                            print(output_one)
                            print(input_one["identifier"])
                        self.assertEqual(output_one["result"], result["result"])
                        self.assertEqual(
                            output_one["description"], result["description"]
                        )
                package = []
            count += 1
        print(outs)
