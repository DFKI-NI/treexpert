# Copyright (c) 2022, DFKI GmbH - all rights reserved

from django.test import TestCase

from core.models import DataType
from tree.models import Color, TreeKind, TreeLeaf, TreeNode, Version

from ..evaluator import FullCriteria


class CriteriaTests(TestCase):
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
            display_name="test_result_one",
            result=False,
        )
        cls.first_leaf.save()
        cls.second_leaf = TreeLeaf(
            tree_version=cls.version,
            number=2,
            display_name="test_result_two",
            result=True,
        )
        cls.second_leaf.save()
        cls.data_type = DataType(name="TEST1", display_name="test type")
        cls.data_type.save()
        cls.color = Color(name="green")
        cls.color.save()
        cls.node = TreeNode(
            tree_version=cls.version,
            number=3,
            display_name="test node",
            description="test description",
            data_type=cls.data_type,
            data_value=20,
            explanation="explain this",
            true_successor=cls.first_leaf,
            false_successor=cls.second_leaf,
            false_color=cls.color,
            false_explanation=" and this!",
        )
        cls.node.save()

    def test_create_criteria(self):
        criteria = FullCriteria(node=self.node, result=True, input=50)
        self.assertEquals(criteria.id, self.node.id)
        self.assertEquals(criteria.number, self.node.number)
        self.assertEquals(criteria.name, self.node.display_name)
        self.assertEquals(criteria.description, self.node.description)
        self.assertEquals(criteria.color, 0)
        self.assertEquals(criteria.data_type, self.node.data_type.id)
        self.assertEquals(criteria.comparison_value, self.node.data_value)
        self.assertEquals(criteria.comparison_method, self.node.comparison)
        self.assertEquals(criteria.list_comparison_method, self.node.list_comparison)
        self.assertEquals(
            criteria.explanation, self.node.explanation + self.node.true_explanation
        )
        self.assertEqual(criteria.result, True)
        self.assertEquals(criteria.input_value, 50)
        self.assertEqual(criteria.based_on, "")

    def test_create_criteria_false_result(self):
        criteria = FullCriteria(node=self.node, result=False, input=18)
        self.assertEquals(criteria.color, self.color.id)
        self.assertEqual(criteria.explanation, "explain this and this!")
        self.assertEqual(criteria.result, False)
        self.assertEqual(criteria.based_on, "")

    def test_create_criteria_node_successor(self):
        node = TreeNode(
            tree_version=self.version,
            number=5,
            display_name="test node node",
            description="testing",
            data_type=self.data_type,
            data_value=40,
            explanation="explaining",
            true_successor=self.node,
            false_successor=self.first_leaf,
        )
        node.save()
        criteria = FullCriteria(node=node, result=True, input=45)
        self.assertEqual(criteria.based_on, self.node.id)
