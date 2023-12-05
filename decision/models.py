from django.db import models

from core.models import DataType
from tree.models import TreeLeaf, Version


class ExpertRequest(models.Model):
    date = models.DateTimeField(auto_now_add=True)
    identifier = models.CharField(max_length=50)
    # used to identify the entity the request was made for
    sec_identifier = models.CharField(max_length=50)
    version = models.ForeignKey(Version, on_delete=models.RESTRICT)

    def __str__(self):
        return (
            self.identifier
            + " ("
            + str(self.id)
            + ") "
            + self.date.strftime("%d.%m.%Y, %H:%M")
        )


class RequestData(models.Model):
    request = models.ForeignKey(ExpertRequest, on_delete=models.CASCADE)
    type = models.ForeignKey(DataType, on_delete=models.RESTRICT)
    value = models.JSONField()


class Decision(models.Model):
    request = models.OneToOneField(ExpertRequest, on_delete=models.CASCADE)
    description = models.CharField(
        max_length=200
    )  # result of end leaf or missing data text
    result = models.BooleanField(null=True)
    end_leaf = models.ForeignKey(
        TreeLeaf, on_delete=models.RESTRICT, blank=True, null=True
    )
    is_preliminary = models.BooleanField()  # data is missing
