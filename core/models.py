from django.db import models


class DataType(models.Model):
    INTEGER = "INT"
    BOOLEAN = "BOOL"
    STRING = "STR"
    KIND_OF_DATA_CHOICES = [
        (INTEGER, "integer"),
        (BOOLEAN, "boolean"),
        (STRING, "string"),
    ]
    name = models.CharField(max_length=20, unique=True)
    display_name = models.CharField(max_length=200)
    kind_of_data = models.CharField(
        max_length=4, choices=KIND_OF_DATA_CHOICES, default=INTEGER
    )
    explanation = models.CharField(max_length=2000)

    def __str__(self):
        return (
            self.name
            + " ("
            + str(self.id)
            + ") "
            + self.kind_of_data
            + self.explanation
        )
