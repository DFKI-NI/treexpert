# Copyright (c) 2021, DFKI GmbH - all rights reserved

from typing import Union
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.db.models.query import QuerySet
from django.db.models.signals import post_init


from core.models import DataType


class TreeKind(models.Model):
    name = models.CharField(max_length=60, unique=True)
    description = models.CharField(max_length=200)


class Color(models.Model):
    name = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.name + " (" + str(self.id) + ")"


class VersionManager(models.Manager):
    """
    used to make sure that a new version for this tree is always bigger than the one
    before. depending on the isMajor(update) variable this will step from 1.0 to 1.1
    or to 2.0
    """

    def get_current_version(self, kind_of_tree: TreeKind) -> "Union[None, Version]":
        # ordered = self.filter(valid=True, deleted=False).order_by("-date_created")
        all_of_this_kind = self.filter(kind_of_tree=kind_of_tree)
        ordered = all_of_this_kind.order_by("-date_created")
        if not ordered:
            return None
        return ordered.first()

    def create_next_version(
        self,
        kind_of_tree: TreeKind,
        isMajor: bool = False,
        is_valid: bool = False,
        delete: bool = False,
    ):
        latest_version = self.get_current_version(kind_of_tree)
        major = 0 if latest_version is None else latest_version.major
        minor = 0 if latest_version is None else latest_version.minor
        if isMajor:
            return self.create(
                kind_of_tree=kind_of_tree,
                major=major + 1,
                minor=0,
                valid=is_valid,
                deleted=delete,
            )
        else:
            return self.create(
                kind_of_tree=kind_of_tree,
                major=major,
                minor=minor + 1,
                valid=is_valid,
                deleted=delete,
            )


class Version(models.Model):
    """
    stores the version information of a tree and the connection to a tree kind.
    a tree is always connected to exactly one version
    """

    kind_of_tree = models.ForeignKey(TreeKind, on_delete=models.CASCADE)
    date_created = models.DateTimeField(auto_now_add=True)
    major = models.IntegerField()
    minor = models.IntegerField()
    valid = models.BooleanField(default=False)
    deleted = models.BooleanField(default=False)

    objects = VersionManager()

    def __str__(self):
        return self.kind_of_tree.name + ": " + str(self.major) + "." + str(self.minor)


class LeafManager(models.Manager):
    """used for the retrieval of all leaves of a version"""

    def get_leafs_of_version(self, version: Version) -> "QuerySet[TreeLeaf]":
        return self.filter(tree_version=version)

    def get_current_leafs(self, kind_of_tree: TreeKind):
        version = Version.objects.get_current_version(kind_of_tree)
        return self.get_leafs_of_version(version)


class TreeLeaf(models.Model):
    number = models.IntegerField()
    date_created = models.DateTimeField(auto_now_add=True)
    id = models.CharField(
        primary_key=True,
        max_length=35,
        default=f"{date_created}_{number}",
    )
    tree_version = models.ForeignKey(Version, on_delete=models.CASCADE)
    display_name = models.CharField(max_length=100)
    result = models.BooleanField()
    color = models.ForeignKey(Color, on_delete=models.SET_NULL, null=True)

    objects = LeafManager()


def id_creator(sender, instance, **kwargs):
    """
    used to create a unique id for the node or leaf that's easily readable for humans.
    for a node this will be sth like 1_1.0_N.1 meaning:
    {tree_kind}_{version}_N(ode).{number} <- the number is the one used to declare
    relations between nodes and leafs before they receive this id.
    for a leaf this will be nearly the same, just switching the N for Node for a L for
    Leaf.
    """
    try:
        instance.id = (
            f"{instance.tree_version.kind_of_tree.id}"
            f"_{instance.tree_version.major}.{instance.tree_version.minor}"
            f"_{str(type(instance))[-6]}.{instance.number}"
        )
    except AttributeError:
        pass


post_init.connect(id_creator, TreeLeaf)


class NodeManager(models.Manager):
    """used for the retrieval of all nodes of a version"""

    def get_nodes_of_version(self, version: Version) -> "QuerySet[TreeNode]":
        return self.filter(tree_version=version)

    def get_current_nodes(self, kind_of_tree: TreeKind):
        version = Version.objects.get_current_version(kind_of_tree)
        return self.get_nodes_of_version(version)


# noinspection SpellCheckingInspection
class TreeNode(models.Model):
    GREATERTHAN = "GT"
    SMALLERTHAN = "ST"
    EQUAL = "EQ"
    NOTEQUAL = "NE"
    COMPARISON_METHODS = [
        (GREATERTHAN, "greater than"),
        (SMALLERTHAN, "smaller than"),
        (EQUAL, "equal"),
        (NOTEQUAL, "not equal"),
    ]

    ALL = "ALL"
    ONE = "ONE"
    TWO = "TWO"
    LIST_COMPARISON_METHODS = [
        (ALL, "all fields"),
        (ONE, "one field"),
        (TWO, "two fields"),
    ]

    number = models.IntegerField()
    date_created = models.DateTimeField(auto_now_add=True)
    id = models.CharField(
        primary_key=True,
        max_length=35,
        default=f"{date_created}_{number}",
    )
    tree_version = models.ForeignKey(Version, on_delete=models.CASCADE)
    display_name = models.CharField(max_length=100)
    description = models.CharField(max_length=300)
    data_type = models.ForeignKey(DataType, on_delete=models.CASCADE)
    data_value = models.JSONField()
    comparison = models.CharField(
        max_length=2, choices=COMPARISON_METHODS, default=GREATERTHAN
    )
    list_comparison = models.CharField(
        max_length=3, choices=LIST_COMPARISON_METHODS, default=ALL, blank=True
    )
    explanation = models.CharField(max_length=700)
    true_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, related_name="true_origin"
    )
    true_id = models.CharField(max_length=35)
    true_successor = GenericForeignKey("true_type", "true_id")
    true_explanation = models.CharField(max_length=700)
    true_color = models.ForeignKey(
        Color, on_delete=models.SET_NULL, null=True, related_name="true_color"
    )
    false_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, related_name="false_origin"
    )
    false_id = models.CharField(max_length=35)
    false_successor = GenericForeignKey("false_type", "false_id")
    false_explanation = models.CharField(max_length=700)
    false_color = models.ForeignKey(
        Color, on_delete=models.SET_NULL, null=True, related_name="false_color"
    )

    objects = NodeManager()

    def __str__(self):
        return str(self.id) + ": " + self.display_name


post_init.connect(id_creator, TreeNode)


class TreeManager(models.Manager):
    """
    used to retreive a complete tree, since this requires some effort
    """

    def get_complete_tree(self, version: Version):
        """
        Returns
        -------
        tree
            the tree object with the version and root information
        nodes
            all the nodes that are used in this tree
        leafs
            all the leaves that are used in this tree
        version
            the version object specified in the tree object
        """
        if version is None:
            return None
        tree = self.filter(tree_version=version).first()
        nodes = TreeNode.objects.get_nodes_of_version(version)
        leafs = TreeLeaf.objects.get_leafs_of_version(version)
        return tree, nodes, leafs, version

    def get_current_complete_tree(self, kind_of_tree):
        version = Version.objects.get_current_version(kind_of_tree)
        return self.get_complete_tree(version)


class Tree(models.Model):
    date_created = models.DateTimeField(auto_now_add=True)
    root = models.OneToOneField("TreeNode", on_delete=models.CASCADE)
    created_by = models.CharField(max_length=50)
    tree_version = models.ForeignKey(Version, on_delete=models.CASCADE)

    objects = TreeManager()

    def __str__(self):
        return str(self.id) + ", " + str(self.date_created)
