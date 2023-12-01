import json
from unittest.mock import patch

from django.test import Client

from core.models import DataType

from tree.api import (
    delete_nodes,
    NewTree,
    PathDate,
    save_nodes,
    TreeNodeIn,
    TreeLeafIn,
    validate_tree,
)
from tree.models import Color, Tree, TreeKind, TreeLeaf, TreeNode, Version
from .test_models import BaseModelTreeTests


class TreeApiTests(BaseModelTreeTests):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client = Client()
        cls.tree = Tree(root=cls.node, created_by="paula", tree_version=cls.version)
        cls.tree.save()

    def test_get_all_colors(self):
        color_two = Color(name="red")
        color_two.save()
        response = self.client.get("/api/tree/colors")
        self.assertEqual(len(response.json()), 2)
        self.assertEqual(response.json()[0]["name"], "green")
        self.assertEqual(response.json()[1]["name"], "red")

    def test_new_color(self):
        new_color = {"name": "blue"}
        response = self.client.post(
            "/api/tree/color/new",
            data=json.dumps(new_color),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "blue")

    @patch("tree.models.Color.objects")
    def test_new_color_use_create(self, mock_color):
        new_color = {"name": "blue"}
        mock_color.create.return_value = Color(id=34, name="blue")
        self.client.post(
            "/api/tree/color/new",
            data=json.dumps(new_color),
            content_type="application/json",
        )
        mock_color.create.assert_called_with(name="blue")

    def test_update_color_response(self):
        color_one = Color(name="test1", id=1)
        color_one.save()
        json_data = {
            "name": "test2",
        }
        response = self.client.put(
            "/api/tree/color/update/1",
            data=json.dumps(json_data, indent=4),
            content_type="application/json",
        )
        self.assertEqual(
            response.json(), "successfully updated color 1 from test1 to test2"
        )
        self.assertEqual(response.status_code, 200)

    def test_update_color(self):
        color_one = Color(name="test1", id=1)
        color_one.save()
        json_data = {
            "name": "test2",
        }
        response = self.client.put(
            "/api/tree/color/update/1",
            data=json.dumps(json_data, indent=4),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        new_color = Color.objects.get(id=1)
        self.assertEqual(new_color.name, "test2")

    def test_get_all_kinds(self):
        kind_two = TreeKind(name="Test Kind 2", description="test description 2")
        kind_two.save()
        response = self.client.get("/api/tree/kind/all")
        self.assertEqual(len(response.json()), 2)
        self.assertEqual(response.json()[0]["name"], "Test Kind")
        self.assertEqual(response.json()[1]["name"], "Test Kind 2")

    def test_get_all_trees(self):
        response = self.client.get("/api/tree/all")
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["created_by"], "paula")
        self.assertEqual(
            response.json()[0]["tree_version"]["minor"], self.version.minor
        )

    def test_complete_tree(self):
        print(self.tree)
        response = self.client.get("/api/tree/latest")
        self.assertEqual(response.json()["created_by"], "paula")
        self.assertNotEqual(len(response.json()["nodes"]), 0)
        self.assertNotEqual(len(response.json()["leafs"]), 0)

    @patch("tree.models.Tree.objects.get_current_complete_tree")
    def test_complete_tree_none(self, mock_tree):
        mock_tree.return_value = None
        response = self.client.get("/api/tree/latest")
        self.assertEqual(response.status_code, 204)

    def test_complete_tree_by_id(self):
        response = self.client.get("/api/tree/id/" + str(self.tree.id))
        self.assertEqual(response.json()["created_by"], "paula")
        self.assertNotEqual(len(response.json()["nodes"]), 0)
        self.assertNotEqual(len(response.json()["leafs"]), 0)

    @patch("tree.models.Tree.objects.get_complete_tree")
    def test_complete_tree_by_id_none(self, mock_tree):
        mock_tree.return_value = None
        response = self.client.get("/api/tree/id/" + str(self.tree.id))
        self.assertEqual(response.status_code, 204)

    def test_path_date_value(self):
        path_date = PathDate(year=2022, month=3, day=5)
        self.assertEqual(str(path_date.value()), "2022-03-05")

    def test_tree_at(self):
        # act
        response = self.client.get("/api/tree/2022/03/05")
        # assert
        self.assertEqual(response.status_code, 418)

    def test_save_nodes(self):
        # arrange
        new_version = Version.objects.create(
            kind_of_tree=self.tree_kind, major=1, minor=0
        )
        leaf_3 = TreeLeaf(
            tree_version=new_version,
            number=3,
            display_name="test_result_3",
            result=False,
        )
        leaf_4 = TreeLeaf(
            tree_version=new_version,
            number=4,
            display_name="test_result_4",
            result=True,
        )
        node_1 = TreeNode(
            tree_version=new_version,
            number=1,
            display_name="first test node",
            description="this is another description",
            data_type=self.data_type,
            data_value="{'value': 'test'}",
            explanation="explain it again",
            true_successor=leaf_3,
            false_successor=leaf_4,
        )
        node_2 = TreeNode(
            tree_version=new_version,
            number=2,
            display_name="second test node",
            description="this is another description",
            data_type=self.data_type,
            data_value="{'value': 'test'}",
            explanation="explain it again",
            true_successor=leaf_3,
            false_successor=leaf_4,
        )
        # act
        save_nodes([node_1, node_2, leaf_3, leaf_4])
        # assert
        leafs = TreeLeaf.objects.filter(tree_version=new_version)
        nodes = TreeNode.objects.filter(tree_version=new_version)
        self.assertEqual(set(leafs), {leaf_3, leaf_4})
        self.assertEqual(set(nodes), {node_1, node_2})

    def test_delete_nodes(self):
        # arrange
        new_version = Version.objects.create(
            kind_of_tree=self.tree_kind, major=1, minor=0
        )
        new_version_str = str(new_version)
        leaf_3 = TreeLeaf(
            tree_version=new_version,
            number=3,
            display_name="test_result_3",
            result=False,
        )
        leaf_4 = TreeLeaf(
            tree_version=new_version,
            number=4,
            display_name="test_result_4",
            result=True,
        )
        leaf_3.save()
        leaf_4.save()
        node_1 = TreeNode(
            tree_version=new_version,
            number=1,
            display_name="first test node",
            description="this is another description",
            data_type=self.data_type,
            data_value="{'value': 'test'}",
            explanation="explain it again",
            true_successor=leaf_3,
            false_successor=leaf_4,
        )
        node_2 = TreeNode(
            tree_version=new_version,
            number=2,
            display_name="second test node",
            description="this is another description",
            data_type=self.data_type,
            data_value="{'value': 'test'}",
            explanation="explain it again",
            true_successor=leaf_3,
            false_successor=leaf_4,
        )
        node_1.save()
        node_2.save()
        # act
        delete_nodes(new_version)
        response = self.client.get("/api/tree/latest")
        # assert
        self.assertNotEqual(response.json()["version"], new_version_str)

    def test_validate_tree(self):
        # assert
        new_version = Version.objects.create(
            kind_of_tree=self.tree_kind, major=1, minor=0
        )
        data_type = DataType(name="test")
        data_type.save()
        leaf_2 = TreeLeaf(
            tree_version=new_version,
            number=2,
            display_name="result_2",
            result=False,
        )
        leaf_3 = TreeLeaf(
            tree_version=new_version,
            number=3,
            display_name="result_3",
            result=True,
        )
        leaf_2.save()
        leaf_3.save()
        node_1 = TreeNode(
            tree_version=new_version,
            number=1,
            display_name="disname",
            description="desc",
            data_type=data_type,
            data_value="{'value': 'test'}",
            explanation="explain this",
            true_successor=leaf_2,
            false_successor=leaf_3,
        )
        node_1.save()
        data_valid = NewTree(
            created_by="jonas",
            new_major_version=False,
            root=1,
            nodes=[
                TreeNodeIn(
                    number=1,
                    display_name="disname",
                    description="desc",
                    data_type_id=data_type.id,
                    data_value=0,
                    comparison="EQ",
                    list_comparison="ALL",
                    explanation="stdexplan",
                    true_number=2,
                    true_explanation="true_expla",
                    true_color_id=2,
                    false_number=3,
                    false_explanation="false_expla",
                    false_color_id=1,
                )
            ],
            leafs=[
                TreeLeafIn(number=2, display_name="result", result=True, color_id=2),
                TreeLeafIn(number=3, display_name="result", result=True, color_id=1),
            ],
        )
        data_invalid = NewTree(
            created_by="jonas",
            new_major_version=False,
            root=1,
            nodes=[
                TreeNodeIn(
                    number=1,
                    display_name="disname",
                    description="desc",
                    data_type_id=data_type.id,
                    data_value="test",
                    comparison="GT",
                    list_comparison="ALL",
                    explanation="stdexplan",
                    true_number=2,
                    true_explanation="true_expla",
                    true_color_id=2,
                    false_number=3,
                    false_explanation="false_expla",
                    false_color_id=1,
                ),
                TreeNodeIn(
                    number=4,
                    display_name="disname",
                    description="desc",
                    data_type_id=data_type.id,
                    data_value="test",
                    comparison="GT",
                    list_comparison="ALL",
                    explanation="stdexplan",
                    true_number=2,
                    true_explanation="true_expla",
                    true_color_id=2,
                    false_number=3,
                    false_explanation="false_expla",
                    false_color_id=1,
                ),
            ],
            leafs=[
                TreeLeafIn(number=2, display_name="result", result=False, color_id=2),
                TreeLeafIn(number=3, display_name="result", result=True, color_id=1),
            ],
        )
        tree = Tree(created_by="me", root=node_1, tree_version=new_version)
        # act
        response_valid_bool, response_valid_message = validate_tree(tree, data_valid)
        response_invalid_bool, response_invalid_message = validate_tree(
            tree, data_invalid
        )
        # assert
        self.assertEqual(response_valid_bool, True)
        self.assertEqual(response_valid_message, "All good")
        self.assertEqual(response_invalid_bool, False)
        self.assertEqual(
            response_invalid_message,
            (
                "number of saved nodes/leafs not like in query.\n"
                "Probably query has two 'roots'.\n"
            ),
        )

    def test_post_tree(self):
        # arrange
        data_type = DataType(name="test")
        data_type.save()
        json_data = {
            "created_by": "paula",
            "new_major_version": True,
            "root": 4,
            "nodes": [
                {
                    "number": 4,
                    "display_name": "test_node",
                    "description": "this is a description",
                    "data_type_id": data_type.id,
                    "data_value": "test",
                    "comparison": "GT",
                    "list_comparison": "ALL",
                    "explanation": "explain this",
                    "true_number": 2,
                    "true_explanation": "",
                    "false_number": 1,
                    "false_explanation": "",
                }
            ],
            "leafs": [
                {"number": 1, "display_name": "test_result_1", "result": False},
                {
                    "number": 2,
                    "display_name": "test_result_2",
                    "result": True,
                    "color": 1,
                },
            ],
        }
        # act
        response = self.client.post(
            "/api/tree/new/" + str(self.tree_kind.id),
            data=json.dumps(json_data, indent=4),
            content_type="application/json",
        )
        # assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["created_by"], "paula")
        self.assertEqual(
            response.json()["tree_version"]["major"], self.version.major + 1
        )

    def test_post_invalid_tree_same_numbers(self):
        # arrange
        data_type = DataType(name="test")
        data_type.save()
        json_data = {
            "created_by": "jonas",
            "new_major_version": False,
            "root": 1,
            "nodes": [
                {
                    "number": 1,
                    "display_name": "disname",
                    "description": "desc",
                    "data_type_id": 2,
                    "data_value": False,
                    "comparison": "EQ",
                    "list_comparison": "ALL",
                    "explanation": "stdexplan",
                    "true_number": 2,
                    "true_explanation": "true_expla",
                    "true_color_id": 2,
                    "false_number": 3,
                    "false_explanation": "false_expla",
                    "false_color_id": 1,
                }
            ],
            "leafs": [
                {"number": 2, "display_name": "result", "result": True, "color_id": 2},
                {"number": 2, "display_name": "result", "result": True, "color_id": 1},
            ],
        }
        # act
        response = self.client.post(
            "/api/tree/new/" + str(self.tree_kind.id),
            data=json.dumps(json_data, indent=4),
            content_type="application/json",
        )
        # assert
        self.assertEqual(
            response.json(), "You have assigned number = 2 to several elements"
        )
        self.assertEqual(response.status_code, 400)

    def test_post_invalid_tree_2_roots(self):
        # arrange
        data_type = DataType(name="test")
        data_type.save()
        json_data = {
            "created_by": "jonas",
            "new_major_version": False,
            "root": 1,
            "nodes": [
                {
                    "number": 1,
                    "display_name": "disname",
                    "description": "desc",
                    "data_type_id": 2,
                    "data_value": False,
                    "comparison": "EQ",
                    "list_comparison": "ALL",
                    "explanation": "stdexplan",
                    "true_number": 3,
                    "true_explanation": "true_expla",
                    "true_color_id": 2,
                    "false_number": 4,
                    "false_explanation": "false_expla",
                    "false_color_id": 1,
                },
                {
                    "number": 2,
                    "display_name": "disname",
                    "description": "desc",
                    "data_type_id": 2,
                    "data_value": False,
                    "comparison": "EQ",
                    "list_comparison": "ALL",
                    "explanation": "stdexplan",
                    "true_number": 4,
                    "true_explanation": "true_expla",
                    "true_color_id": 2,
                    "false_number": 5,
                    "false_explanation": "false_expla",
                    "false_color_id": 1,
                },
            ],
            "leafs": [
                {"number": 3, "display_name": "result", "result": True, "color_id": 2},
                {"number": 4, "display_name": "result", "result": True, "color_id": 1},
                {"number": 5, "display_name": "result", "result": True, "color_id": 1},
            ],
        }
        # act
        response = self.client.post(
            "/api/tree/new/" + str(self.tree_kind.id),
            data=json.dumps(json_data, indent=4),
            content_type="application/json",
        )
        # assert
        self.assertEqual(
            response.json(),
            (
                "number of saved nodes/leafs not like in query.\n"
                "Probably query has two 'roots'.\n"
                "The tree could not be validated and saved correctly.\n"
                "Change what is wrong and try again!"
            ),
        )
        self.assertEqual(response.status_code, 400)

    def test_post_invalid_tree_nonexisting_successor(self):
        # arrange
        data_type = DataType(name="test")
        data_type.save()
        json_data = {
            "created_by": "jonas",
            "new_major_version": False,
            "root": 1,
            "nodes": [
                {
                    "number": 1,
                    "display_name": "disname",
                    "description": "desc",
                    "data_type_id": 2,
                    "data_value": False,
                    "comparison": "EQ",
                    "list_comparison": "ALL",
                    "explanation": "stdexplan",
                    "true_number": 2,
                    "true_explanation": "true_expla",
                    "true_color_id": 1,
                    "false_number": 3,
                    "false_explanation": "false_expla",
                    "false_color_id": 2,
                },
            ],
            "leafs": [
                {"number": 3, "display_name": "result", "result": True, "color_id": 2},
            ],
        }
        # act
        response = self.client.post(
            "/api/tree/new/" + str(self.tree_kind.id),
            data=json.dumps(json_data, indent=4),
            content_type="application/json",
        )
        # assert
        self.assertEqual(
            response.json(),
            (
                "You referenced 2 as successor of a node, "
                "but you didn't define a Leaf or Node with that number."
                "\nChange what is wrong and try again!"
            ),
        )
        self.assertEqual(response.status_code, 400)

    def test_post_invalid_tree_recursion_error(self):
        # arrange
        data_type = DataType(name="test")
        data_type.save()
        json_data = {
            "created_by": "jonas",
            "new_major_version": False,
            "root": 1,
            "nodes": [
                {
                    "number": 1,
                    "display_name": "disname",
                    "description": "desc",
                    "data_type_id": 2,
                    "data_value": False,
                    "comparison": "EQ",
                    "list_comparison": "ALL",
                    "explanation": "stdexplan",
                    "true_number": 2,
                    "true_explanation": "true_expla",
                    "true_color_id": 2,
                    "false_number": 3,
                    "false_explanation": "false_expla",
                    "false_color_id": 1,
                },
                {
                    "number": 2,
                    "display_name": "disname",
                    "description": "desc",
                    "data_type_id": 2,
                    "data_value": False,
                    "comparison": "EQ",
                    "list_comparison": "ALL",
                    "explanation": "stdexplan",
                    "true_number": 3,
                    "true_explanation": "true_expla",
                    "true_color_id": 2,
                    "false_number": 5,
                    "false_explanation": "false_expla",
                    "false_color_id": 1,
                },
                {
                    "number": 3,
                    "display_name": "disname",
                    "description": "desc",
                    "data_type_id": 2,
                    "data_value": False,
                    "comparison": "EQ",
                    "list_comparison": "ALL",
                    "explanation": "stdexplan",
                    "true_number": 5,
                    "true_explanation": "true_expla",
                    "true_color_id": 2,
                    "false_number": 2,
                    "false_explanation": "false_expla",
                    "false_color_id": 1,
                },
            ],
            "leafs": [
                {"number": 5, "display_name": "result", "result": True, "color_id": 1}
            ],
        }
        # act
        response = self.client.post(
            "/api/tree/new/" + str(self.tree_kind.id),
            data=json.dumps(json_data, indent=4),
            content_type="application/json",
        )
        # assert
        self.assertEqual(
            response.json(),
            (
                "RecursionError: There is a endless recursion loop in your tree.\n"
                "Change what is wrong and try again!"
            ),
        )
        self.assertEqual(response.status_code, 400)

    def test_explanation_tree(self):
        # act
        response = self.client.get("/api/tree/explanation")
        # assert
        self.assertEqual(response.json()["version"], str(self.version))
        self.assertEqual(response.json()["nodes"][0]["id"], self.node.id)
        self.assertEqual(response.json()["leafs"][0]["id"], self.first_leaf.id)
        self.assertEqual(response.json()["leafs"][1]["id"], self.second_leaf.id)

    def test_explanation_tree_half_version(self):
        # act
        response_major = self.client.get("/api/tree/explanation", {"major": 1})
        response_minor = self.client.get("/api/tree/explanation", {"minor": 1})
        # assert
        self.assertEqual(response_major.status_code, 400)
        self.assertEqual(response_minor.status_code, 400)

    @patch("tree.models.Tree.objects.get_complete_tree")
    def test_explanation_tree_with_version(self, mock_tree):
        # arrange
        mock_tree.return_value = None
        # act
        response = self.client.get(
            "/api/tree/explanation",
            {"major": self.version.major, "minor": self.version.minor},
        )
        # assert
        assert mock_tree.called
        self.assertEqual(response.status_code, 204)

    @patch("tree.models.Tree.objects.get_current_complete_tree")
    def test_explanation_tree_none(self, mock_tree):
        # arrange
        mock_tree.return_value = None
        # act
        response = self.client.get("/api/tree/explanation")
        # assert
        self.assertEqual(response.status_code, 204)
