from typing import Type, Union
from dataclasses import dataclass
import hashlib

@dataclass
class Object:
    """Base class for shared attributes."""
    id: int
    forname: str
    surname: str
    street: str
    housenumber: str
    postcode: str
    region: str
    lat: float
    lon: float

@dataclass
class School(Object):
    """Represent a school with relevant attributes."""
    pass

@dataclass
class Child(Object):
    """Represent a child with relevant attributes."""
    school_id: int
    tour_id: int

def create_object_id(obj: Object) -> str:
    """Create a unique ID based on forname, surname, street, and housenumber."""
    unique_string = f"{obj.forname}{obj.surname}{obj.street}{obj.housenumber}"
    return hashlib.md5(unique_string.encode('utf-8')).hexdigest()

def create_object(row: dict, obj_class: Type[Union[Child, School]]) -> Union[Child, School]:
    """Create an object (Child or School) from a dictionary row."""
    base_attributes = {
        "id": 0,  # Temporary ID for hashing
        "forname": row['fornames'],
        "surname": row['surnames'],
        "street": row['streets'],
        "housenumber": row['housenumbers'],
        "postcode": row['postcodes'],
        "region": row['regions'],
        "lat": row.get('lat', None),
        "lon": row.get('lon', None),
    }
    base_object = Object(**base_attributes)
    base_attributes["id"] = create_object_id(base_object)

    if obj_class == Child:
        return Child(
            **base_attributes,
            school_id=row.get("school_id", None),
            tour_id=int(row["tour_id"]),
        )
    elif obj_class == School:
        return School(**base_attributes)
    else:
        raise ValueError("Unsupported object class.")