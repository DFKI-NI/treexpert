from django.contrib import admin

from .models import Color, Tree, TreeKind, TreeLeaf, TreeNode, Version

admin.site.register(Color)
admin.site.register(Tree)
admin.site.register(TreeKind)
admin.site.register(TreeLeaf)
admin.site.register(TreeNode)
admin.site.register(Version)
