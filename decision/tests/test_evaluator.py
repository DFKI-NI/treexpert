# Copyright (c) 2022, DFKI GmbH - all rights reserved

from django.test import TestCase

from core.models import DataType
from tree.models import Tree, TreeKind, TreeLeaf, TreeNode, Version

from ..evaluator import Evaluator, EvaluatorException


class EvaluatorTests(TestCase):
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
        cls.evaluator = Evaluator(
            tree=cls.tree,
            nodes=[cls.node],
            leafs=[cls.first_leaf, cls.second_leaf],
        )

    def test_create_evaluator(self):
        self.assertEquals(self.evaluator.root, self.node.id)
        self.assertIsNone(self.evaluator.end_leaf)
        self.assertIsNone(self.evaluator.missing_data)
        self.assertIsNone(self.evaluator.node_missing_sth)
        self.assertEquals(self.evaluator.criteria, [])
        self.assertEquals(len(self.evaluator.tree_dict), 3)

    def test_reset_evaluator(self):
        self.evaluator.criteria = [1, 2, 3]
        self.evaluator.end_leaf = self.first_leaf
        self.evaluator.missing_data = 2
        self.evaluator.node_missing_sth = self.node
        self.evaluator.reset_evaluator()
        self.assertIsNone(self.evaluator.end_leaf)
        self.assertEqual(self.evaluator.criteria, [])
        self.assertIsNone(self.evaluator.missing_data)
        self.assertIsNone(self.evaluator.node_missing_sth)

    def test_evaluate_node_int(self):
        result_single = self.evaluator.evaluate_node(node=self.node, data=600000)
        result_list = self.evaluator.evaluate_node(
            node=self.node, data=[789234, 700002, 700001]
        )
        self.assertTrue(result_list)
        self.assertFalse(result_single)

    def test_evaluate_node_boolean(self):
        result_single = self.evaluator.evaluate_node(node=self.boolean_node, data=False)
        self.assertFalse(result_single)

    def test_evaluate_node_not_equal(self):
        ne_node = TreeNode(
            tree_version=self.version,
            number=12,
            display_name="test not equal",
            description="stuff",
            data_type=self.data_type,
            data_value=5,
            comparison=TreeNode.NOTEQUAL,
            explanation="explain it!",
            true_successor=self.first_leaf,
            false_successor=self.second_leaf,
        )
        ne_node.save()
        result_true = self.evaluator.evaluate_node(node=ne_node, data=1)
        result_boolean = self.evaluator.evaluate_node(node=ne_node, data=True)
        result_false = self.evaluator.evaluate_node(node=ne_node, data=5)
        self.assertTrue(result_true)
        self.assertTrue(result_boolean)
        self.assertFalse(result_false)

    def test_evaluate_node_raise_error(self):
        error_node = TreeNode(
            number=12,
            display_name="test not equal",
            description="stuff",
            data_type=self.data_type,
            data_value=5,
            comparison="NN",
            explanation="explain it!",
            true_successor=self.first_leaf,
            false_successor=self.second_leaf,
        )
        with self.assertRaises(EvaluatorException):
            self.evaluator.evaluate_node(node=error_node, data=5)

    def test_evaluate_node_boolean_list_true(self):
        result_list_true = self.evaluator.evaluate_node(
            node=self.boolean_node, data=[True, True, True]
        )
        self.assertTrue(result_list_true)

    def test_evaluate_node_boolean_list_false(self):
        result_list_false = self.evaluator.evaluate_node(
            node=self.boolean_node, data=[True, False]
        )
        self.assertFalse(result_list_false)

    def test_evaluate_node_boolean_number(self):
        result_true = self.evaluator.evaluate_node(node=self.boolean_node, data=1)
        result_false = self.evaluator.evaluate_node(node=self.boolean_node, data=0)
        self.assertTrue(result_true)
        self.assertFalse(result_false)

    def test_evaluate_node_for_one_list_comparison(self):
        one_node = TreeNode(
            tree_version=self.version,
            number=11,
            display_name="one_list_comparison_node",
            description="this is a one list comparison node",
            data_type=self.data_type,
            data_value=100,
            comparison=TreeNode.SMALLERTHAN,
            list_comparison=TreeNode.ONE,
            explanation="test explanation",
            true_successor=self.first_leaf,
            false_successor=self.second_leaf,
        )
        one_node.save()
        result_true = self.evaluator.evaluate_node(
            node=one_node, data=[89, 100, 234, 8763434]
        )
        result_false = self.evaluator.evaluate_node(node=one_node, data=[88, 89, 90])
        result_one_element = self.evaluator.evaluate_node(node=one_node, data=[-1])
        self.assertTrue(result_true)
        self.assertFalse(result_false)
        self.assertTrue(result_one_element)

    def test_evaluate_node_for_two_list_comparison(self):
        two_node = TreeNode(
            tree_version=self.version,
            number=11,
            display_name="one_list_comparison_node",
            description="this is a one list comparison node",
            data_type=self.data_type,
            data_value=100,
            comparison=TreeNode.SMALLERTHAN,
            list_comparison=TreeNode.TWO,
            explanation="test explanation",
            true_successor=self.first_leaf,
            false_successor=self.second_leaf,
        )
        two_node.save()
        result_true = self.evaluator.evaluate_node(
            node=two_node, data=[89, 100, 90, 8763434]
        )
        result_false = self.evaluator.evaluate_node(node=two_node, data=[88, 89, 90])
        result_one_element = self.evaluator.evaluate_node(node=two_node, data=[-1])
        result_two_elements = self.evaluator.evaluate_node(node=two_node, data=[2, 3])
        self.assertTrue(result_true)
        self.assertFalse(result_false)
        self.assertFalse(result_one_element)
        self.assertTrue(result_two_elements)
