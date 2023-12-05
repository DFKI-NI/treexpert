# Copyright (c) 2022, DFKI GmbH - all rights reserved

from django.test import TestCase

from core.models import DataType
from tree.models import TreeKind, TreeLeaf, Version

from ..models import ExpertRequest, RequestData, Decision


class DecisionModelTests(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.tree_kind = TreeKind(name="Test Kind", description="test description")
        cls.tree_kind.save()
        cls.version = Version(kind_of_tree=cls.tree_kind, major=0, minor=1)
        cls.version.save()
        cls.request = ExpertRequest(
            identifier="test_id", sec_identifier="testing_id", version=cls.version
        )
        cls.request.save()

    def test_expert_request_create(self):
        # assert
        self.assertEqual(self.request.sec_identifier, "testing_id")
        self.assertEqual(self.request.identifier, "test_id")
        self.assertIsNotNone(self.request.date)

    def test_expert_request_print(self):
        # assert
        self.assertTrue(
            str(self.request).startswith("test_id (" + str(self.request.id) + ")")
        )
        self.assertEqual(self.request.identifier, "test_id")
        self.assertIsNotNone(self.request.date)

    def test_expert_data_create(self):
        # arrange
        data_type = DataType(
            name="TEST",
            display_name="Test Data Type",
            explanation="explain this!",
        )
        data_type.save()
        # act
        data = RequestData(request=self.request, type=data_type, value=5)
        data.save()
        # assert
        self.assertEqual(data.request.id, self.request.id)
        self.assertEqual(data.type.id, data_type.id)
        self.assertEqual(data.value, 5)

    def test_decision_create(self):
        # arrange

        leaf = TreeLeaf(
            tree_version=self.version,
            number=1,
            display_name="test_result1",
            result=False,
        )
        leaf.save()
        # act
        decision = Decision(
            request=self.request,
            description="test result",
            result=leaf.result,
            end_leaf=leaf,
            is_preliminary=True,
        )
        decision.save()
        # assert
        self.assertEqual(decision.request.id, self.request.id)
        self.assertEqual(decision.description, "test result")
        self.assertEqual(decision.result, leaf.result)
        self.assertEqual(decision.end_leaf.id, leaf.id)
        self.assertTrue(decision.is_preliminary)
