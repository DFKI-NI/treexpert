from django.test import TestCase

from core.models import DataType
from tree.models import Color, Tree, TreeKind, TreeLeaf, TreeNode, Version


class ColorModelTests(TestCase):
    def test_color_is_named_correctly(self):
        new_color = Color(name="test")
        self.assertIs(new_color.name, "test")
        self.assertEquals(str(new_color), "test (None)")

    def test_color_gets_id_when_saved(self):
        new_color = Color(name="test")
        new_color.save()
        self.assertNotEquals(str(new_color), "test (None)")


class VersionModelTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super(VersionModelTests, cls).setUpClass()
        cls.tree_kind = TreeKind(name="Test Kind", description="test description")
        cls.tree_kind.save()

    def test_version_name_is_correct(self):
        new_version = Version(kind_of_tree=self.tree_kind, major=2, minor=3)
        self.assertEquals(str(new_version), "Test Kind: 2.3")

    def test_version_has_date_created_field(self):
        new_version = Version(kind_of_tree=self.tree_kind, major=1, minor=2)
        self.assertIsNone(new_version.date_created)
        new_version.save()
        self.assertIsNotNone(new_version.date_created)

    def test_get_current_version_none(self):
        result = Version.objects.get_current_version(kind_of_tree=self.tree_kind)
        self.assertIsNone(result)

    def test_get_current_version_latest(self):
        old_version = Version(kind_of_tree=self.tree_kind, major=0, minor=1)
        old_version.save(force_insert=True)
        next_version = Version(kind_of_tree=self.tree_kind, major=1, minor=0)
        next_version.save(force_insert=True)
        current_version = Version.objects.get_current_version(
            kind_of_tree=self.tree_kind
        )
        self.assertEquals(current_version, next_version)

    def test_create_next_version_first(self):
        first_version = Version.objects.create_next_version(kind_of_tree=self.tree_kind)
        self.assertEquals(first_version.major, 0)
        self.assertEquals(first_version.minor, 1)

    def test_create_next_version_second(self):
        first_version = Version(kind_of_tree=self.tree_kind, major=0, minor=1)
        first_version.save()
        second_version = Version.objects.create_next_version(
            kind_of_tree=self.tree_kind
        )
        self.assertEquals(second_version.major, 0)
        self.assertEquals(second_version.minor, 2)

    def test_create_next_version_major(self):
        first_version = Version(kind_of_tree=self.tree_kind, major=0, minor=1)
        first_version.save()
        second_version = Version.objects.create_next_version(
            kind_of_tree=self.tree_kind, isMajor=True
        )
        self.assertEquals(second_version.major, 1)
        self.assertEquals(second_version.minor, 0)


class BaseModelTreeTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super(BaseModelTreeTests, cls).setUpClass()
        cls.tree_kind = TreeKind(name="Test Kind", description="test description")
        cls.tree_kind.save()
        cls.version = Version(kind_of_tree=cls.tree_kind, major=0, minor=1)
        cls.version.save()
        cls.first_leaf = TreeLeaf(
            tree_version=cls.version,
            number=1,
            display_name="test_result_1",
            result=False,
        )
        cls.first_leaf.save()
        cls.color = Color(name="green")
        cls.color.save()
        cls.second_leaf = TreeLeaf(
            tree_version=cls.version,
            number=2,
            display_name="test_result_2",
            result=True,
            color=cls.color,
        )
        cls.second_leaf.save()
        cls.data_type = DataType(name="TEST", display_name="test type")
        cls.data_type.save()
        cls.node = TreeNode(
            tree_version=cls.version,
            number=4,
            display_name="test_node",
            description="this is a description",
            data_type=cls.data_type,
            data_value="{'value': 'test'}",
            explanation="explain this",
            true_successor=cls.first_leaf,
            false_successor=cls.second_leaf,
        )
        cls.node.save()


class TreeLeafModelTests(BaseModelTreeTests):
    def test_leaf_creation(self):
        self.assertEquals(self.first_leaf.id, str(self.tree_kind.id) + "_" + "0.1_L.1")
        self.assertEquals(self.first_leaf.number, 1)
        self.assertEquals(self.second_leaf.number, 2)

    def test_get_leafs_of_version(self):
        version = Version.objects.get_current_version(kind_of_tree=self.tree_kind)
        result = TreeLeaf.objects.get_leafs_of_version(version)
        self.assertEquals(len(result), 2)
        self.assertEquals(result.first().tree_version, version)

    def test_get_current_leafs(self):
        new_version = Version.objects.create(
            kind_of_tree=self.tree_kind, major=1, minor=0
        )
        third_leaf = TreeLeaf(
            tree_version=new_version,
            number=1,
            display_name="test_result_3",
            result=False,
        )
        third_leaf.save()
        result = TreeLeaf.objects.get_current_leafs(kind_of_tree=self.tree_kind)
        self.assertEquals(len(result), 1)
        self.assertEquals(result.first().tree_version, new_version)


class TreeNodeModelTests(BaseModelTreeTests):
    def test_node_creation(self):
        self.assertEquals(self.node.id, str(self.tree_kind.id) + "_" + "0.1_N.4")
        self.assertEquals(self.node.number, 4)

    def test_get_nodes_of_version(self):
        new_version = Version.objects.create(
            kind_of_tree=self.tree_kind, major=1, minor=0
        )
        second_node = TreeNode(
            tree_version=new_version,
            number=5,
            display_name="second test node",
            description="this is another description",
            data_type=self.data_type,
            data_value="{'value': 'test'}",
            explanation="explain it again",
            true_successor=self.second_leaf,
            false_successor=self.first_leaf,
        )
        second_node.save()
        result = TreeNode.objects.get_nodes_of_version(self.version)
        self.assertEquals(result.first().number, 4)

    def test_get_current_nodes(self):
        new_version = Version.objects.create(
            kind_of_tree=self.tree_kind, major=1, minor=0
        )
        second_node = TreeNode(
            tree_version=new_version,
            number=5,
            display_name="second test node",
            description="this is another description",
            data_type=self.data_type,
            data_value="{'value': 'test'}",
            explanation="explain it again",
            true_successor=self.second_leaf,
            false_successor=self.first_leaf,
        )
        second_node.save()
        result = TreeNode.objects.get_current_nodes(self.tree_kind)
        self.assertEquals(result.first().number, 5)

    def test_str_method(self):
        string = str(self.node)
        self.assertEqual(string, str(self.node.id) + ": test_node")


class TreeManagerTests(TestCase):
    def test_no_version(self):
        result = Tree.objects.get_complete_tree(version=None)
        self.assertIsNone(result)


class TreeModelTests(BaseModelTreeTests):
    def test_tree_creation(self):
        tree = Tree(tree_version=self.version, root=self.node, created_by="test")
        self.assertEquals(str(tree), "None, None")
        tree.save()
        self.assertNotEquals(str(tree), "None, None")
