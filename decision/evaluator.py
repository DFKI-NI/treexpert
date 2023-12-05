import logging
from typing import List, Union

from django.contrib.contenttypes.models import ContentType

from core.models import DataType
from tree.models import Tree, TreeLeaf, TreeNode
from .models import RequestData

logger = logging.getLogger(__name__)


class EvaluatorException(BaseException):
    def __init__(self, message):
        self.message = message


class FullCriteria:
    id: str  # id of the node
    number: int  # number of the node
    name: str
    description: str
    color: int = 0
    data_type: int
    comparison_value: any
    comparison_method: str
    list_comparison_method: str
    explanation: str
    input_value: any
    result: bool
    based_on: str

    def __init__(self, node: TreeNode, result: bool, input: any):
        self.id = node.id
        self.number = node.number
        self.name = node.display_name
        self.description = node.description
        self.data_type = node.data_type.id
        self.comparison_value = node.data_value
        self.comparison_method = node.comparison
        self.list_comparison_method = node.list_comparison
        self.result = result
        # set values that are specific to result
        # based_on only is set for nodes that end in another node
        # the last node with a leaf as the successor gets a 0
        if result:
            self.color = node.true_color.id if node.true_color is not None else 0
            self.explanation = node.explanation + node.true_explanation
            self.based_on = (
                node.true_id
                if node.true_type.id == ContentType.objects.get(model="treenode").id
                else ""
            )
        else:
            self.color = node.false_color.id if node.false_color is not None else 0
            self.explanation = node.explanation + node.false_explanation
            self.based_on = (
                node.false_id
                if node.false_type.id == ContentType.objects.get(model="treenode").id
                else ""
            )
        self.input_value = input


def add_list_to_dict(mylist: List[Union[TreeNode, TreeLeaf]], mydict: dict) -> dict:
    for element in mylist:
        if mydict.get(element.id) is not None:
            raise EvaluatorException("error parsing current tree, duplicate elements")
        mydict[element.id] = element
    return mydict


class Evaluator:
    root: str
    tree_dict: dict
    criteria: List[FullCriteria] = []
    end_leaf: TreeLeaf = None
    missing_data: DataType = None
    node_missing_sth: TreeNode = None

    def __init__(self, tree: Tree, nodes: List[TreeNode], leafs: List[TreeLeaf]):
        self.root = tree.root.id
        tree_dict = dict()
        tree_dict = add_list_to_dict(list(nodes) + list(leafs), tree_dict)
        self.tree_dict = tree_dict

    def evaluate_node(self, node: TreeNode, data):
        # handle nodes with a list as data
        if isinstance(data, list):
            comparisons = [self.evaluate_node(node, element) for element in data]
            if node.list_comparison == node.ONE:
                return True if sum(comparisons) == 1 else False
            elif node.list_comparison == node.TWO:
                return True if sum(comparisons) == 2 else False
            elif node.list_comparison == node.ALL or node.list_comparison is None:
                return True if sum(comparisons) == len(data) else False
            else:
                return True if sum(comparisons) != 0 else False
        # handle single data objects
        else:
            if node.comparison == node.GREATERTHAN:
                return data > node.data_value
            elif node.comparison == node.SMALLERTHAN:
                return data < node.data_value
            elif node.comparison == node.EQUAL:
                return data == node.data_value
            elif node.comparison == node.NOTEQUAL:
                return data != node.data_value
            else:
                raise EvaluatorException("error while evaluating")

    def reset_evaluator(self):
        """
        keep tree, but reset everything that was specific to one entity
        """
        self.criteria = []
        self.end_leaf = None
        self.missing_data = None
        self.node_missing_sth = None

    def run_tree(self, data: List[RequestData]):
        """
        input: data = the list of available information about one entity
        run the tree for one specific entity
        """
        self.reset_evaluator()

        current_node = self.tree_dict[self.root]
        decoded_data = dict()

        # get all the decoded data
        for value in data:
            if decoded_data.get(value.type.id) is not None:
                raise EvaluatorException("error evaluating with this data")
            decoded_data[value.type.id] = value

        # run from node to node until a leaf is reached or no data is available
        while isinstance(current_node, TreeNode) and self.missing_data is None:
            # logger.debug(str(current_node.id) + ": " + current_node.display_name)
            # check if necessary data for this node is available
            necessary_data = decoded_data.get(current_node.data_type.id)
            if necessary_data is None:
                self.missing_data = current_node.data_type
                self.node_missing_sth = current_node
            else:
                # evaluate node and add it + result to criteria list
                evaluation = self.evaluate_node(
                    current_node, decoded_data[current_node.data_type.id].value
                )
                self.criteria.append(
                    FullCriteria(
                        node=current_node,
                        result=evaluation,
                        input=decoded_data[current_node.data_type.id].value,
                    )
                )
                # determine next node or leaf
                if evaluation:
                    current_node = self.tree_dict[current_node.true_id]
                else:
                    current_node = self.tree_dict[current_node.false_id]

        # concluding with the result
        if self.missing_data is None:
            self.end_leaf = current_node
