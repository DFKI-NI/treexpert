import json

from django.test import Client, TestCase

from .models import DataType


class DataTypeModelTests(TestCase):
    def test_data_type_is_named_correctly(self):
        new_data_type = DataType(name="test")
        self.assertIs(new_data_type.name, "test")
        self.assertEquals(str(new_data_type), "test (None) INT")


class CoreApiTests(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        return super().setUp()

    def test_return_all_data_types(self):
        type_one = DataType(name="test1")
        type_two = DataType(name="test2")
        type_one.save()
        type_two.save()
        response = self.client.get("/api/core/datatype/all")
        self.assertEqual(len(response.json()), 2)
        self.assertEqual(response.json()[0]["name"], "test1")
        self.assertEqual(response.json()[1]["name"], "test2")
        self.assertEqual(response.status_code, 200)

    def test_return_data_types_by_id(self):
        type_one = DataType(name="test1", id=1)
        type_two = DataType(name="test2", id=2)
        type_one.save()
        type_two.save()
        response1 = self.client.get("/api/core/datatype/id/1")
        response2 = self.client.get("/api/core/datatype/id/2")
        response3 = self.client.get("/api/core/datatype/id/3")
        self.assertEqual(response1.json()["name"], "test1")
        self.assertEqual(response2.json()["name"], "test2")
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)
        self.assertEqual(response3.status_code, 404)

    def test_add_new_data_type(self):
        json_data = {
            "name": "Namestring",
            "display_name": "disname",
            "kind_of_data": "INT",
            "explanation": "explanation",
        }
        response = self.client.post(
            "/api/core/datatype/new",
            data=json.dumps(json_data, indent=4),
            content_type="application/json",
        )
        self.assertEqual(response.json()["name"], "Namestring")
        self.assertEqual(response.json()["display_name"], "disname")
        self.assertEqual(response.json()["kind_of_data"], "INT")
        self.assertEqual(response.json()["explanation"], "explanation")
        self.assertIsNotNone(response.json()["id"])
        self.assertEqual(response.status_code, 200)

    def test_update_datatype(self):
        type_one = DataType(name="test1", id=1)
        type_one.save()
        json_data = {
            "name": "Namestring",
            "display_name": "disname",
            "kind_of_data": "STR",
            "explanation": "explanation",
        }
        response = self.client.put(
            "/api/core/datatype/update/1",
            data=json.dumps(json_data, indent=4),
            content_type="application/json",
        )
        self.assertEqual(response.json()["name"], "Namestring")
        self.assertEqual(response.json()["display_name"], "disname")
        self.assertEqual(response.json()["kind_of_data"], "STR")
        self.assertEqual(response.json()["explanation"], "explanation")
        self.assertEqual(response.json()["id"], 1)
        self.assertEqual(response.status_code, 200)


class CoreViewTests(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        return super().setUp()

    def test_redirect_to_docs(self):
        response = self.client.get("/")
        self.assertRedirects(response, "/api/docs")
