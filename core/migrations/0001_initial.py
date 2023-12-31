# Generated by Django 4.2.7 on 2023-12-01 10:39

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="DataType",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=20, unique=True)),
                ("display_name", models.CharField(max_length=200)),
                (
                    "kind_of_data",
                    models.CharField(
                        choices=[
                            ("INT", "integer"),
                            ("BOOL", "boolean"),
                            ("STR", "string"),
                        ],
                        default="INT",
                        max_length=4,
                    ),
                ),
                ("explanation", models.CharField(max_length=2000)),
            ],
        ),
    ]
