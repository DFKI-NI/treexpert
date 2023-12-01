from typing import List

from ninja import ModelSchema, Router
from ninja.orm import create_schema
from django.shortcuts import get_object_or_404

from .models import DataType

router = Router(tags=["core"])


# === /datatype/all === get all data types ====================================
DataTypeOut = create_schema(
    DataType,
    name="DataTypeOut",
    fields=["id", "name", "display_name", "kind_of_data", "explanation"],
)


# === /datatype/all === get a list of all data types ==========================
@router.get("/datatype/all", response=List[DataTypeOut])
def get_all_datatypes(request):
    """
    Retrieves all datatypes that exist in the database. The **id** is used as a
    primary key, though the **name** also needs to be unique. The
    **display_name** and **explanation** are supposed to be shown to a user.
    The property **kind_of_data** specifies what kind of data type is expected,
    e.g. integer, boolean, ... This data type will NOT be enforced, it is just
    a hint!
    """
    return DataType.objects.all()


# === /datatypes/#id === get data type by id===================================
@router.get("/datatype/id/{id}", response=DataTypeOut)
def get_datatype_by_id(request, id: int):
    """
    This returns one data type by id. For more information on the properties of
    a data type, see /datatype/all or /datatype/new.
    """
    return get_object_or_404(DataType, id=id)


class DataTypeIn(ModelSchema):
    class Meta:
        model = DataType
        exclude = ["id"]


# === /datatype/new === add new data type =====================================
@router.post("/datatype/new", response={200: DataTypeOut})
def create_new_datatype(request, data_type: DataTypeIn):
    """
    Create a new data type that can then be used in the decision trees with the
    following attributes:
    - **name**: short, used to identify the data type together with id
    - **display_name**: longer name that will be shown to users
    - **explanation**: what is this data type about, for booleans use a question
    - **kind_of_data**: expected basic data type (int, bool, ...) for this data
      type (NOT enforced!)
    """
    new_data_type = DataType.objects.create(**data_type.dict())
    return 200, new_data_type


class DataTypeUpdate(ModelSchema):
    class Meta:
        model = DataType
        fields = ["name", "display_name", "kind_of_data", "explanation"]
        fields_optional = ["name", "display_name", "kind_of_data", "explanation"]


# === /datatype/update === update data type ======================================
@router.put("/datatype/update/{id}", response={200: DataTypeOut})
def update_datatype(request, id: int, data_type: DataTypeUpdate):
    """
    Change a datatype. Just specify the values that you want to change.
    """
    dtype = get_object_or_404(DataType, id=id)
    print(dtype)
    print(data_type.dict())
    print(data_type.dict(exclude_unset=True))
    for attr, value in data_type.dict(exclude_unset=True).items():
        print(attr, value)
        setattr(dtype, attr, value)
    dtype.save()
    return 200, dtype


# === /datatype/#name === get data type by name ==============================
@router.get("/datatype/name/{str:name}", response=DataTypeOut)
def get_datatype_by_name(request, name: str):
    """
    This returns one data type by its name. For more information on the properties
    of a data type, see /datatype/all or /datatype/new.
    """
    return get_object_or_404(DataType, name=name)
