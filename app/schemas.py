from datetime import datetime
from typing import Annoted, Literal, Optional

from bson import ObjectId
from bson.errors import InvalidId
from flask import jsonify
from pydantic import BaseModel, ConfigDict, StringConstraints, ValidationError

PRIORITIES = ('low', 'medium', 'high', 'urgent')
PRIORITIES = {p: i for i, p in enumerate(PRIORITIES)}
ROLES = ('customer', 'agent', 'supervisor','admin')
#stutuses that count toward an agent workload 
ACTIVE_STATUSES = ('assigned', 'in_progress','pending_customer', 'escalated')
##every status except the finished ones:
OPEN_STATUSES = ('new', 'open') + ACTIVE_STATUSES

Email = Annoted[str, StringConstraints(strip_whitespace = True, to_lower =True, max_length= 254)]

def text(lo, hi):
    return Annoted[str, StringConstraints(strip_whitespace=True, min_length=lo, max_length =hi)]

class Strict(BaseModel):
    #extra = 'forbid': unknown fields are an error, not silently ignored. A customer who sends
    #{'customer_id': ..., 'priority': 'urgent'} gets a 422 instead of a quiet noop
    model_config = ConfigDict(exta='forbid')
class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message= message

def ok(data=None, message='OK', status= 200):
    return jsonify({'success': True, 'data': data, 'message': message}),status 

def serialize(value):
    #makes MongoDB documents json-safe: object id => str, datetime -> ISO text, and "-id" is dropped .
    if isinstance(value, dict):
        return{k: serialize(v)for k, v in value.items() if k!= '_id'}
    if isinstance(value, (list,tuple)):
        return [serialize(v) for v in value]
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value

def parse(model, payload):
    #validates a json body against a pydantic model raises apierror so the response is niform.
    if not isinstance(payload, dict) :
        raise ApiError(400, 'Request body must be  json object.')
    try: 
        return model.model_validate(payload)
    except ValidationError as e:
        problems = ';'.join('%s:%s' % ('.'.join(str(p)for p in x['loc'])) or ('body',x['msg']) for x in e.errors)
        raise ApiError(422, problems)   #field names and messages only: never echo the submitted values

def to_object_id(value):
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        raise ApiError(400, 'Invalid identifier.')

class loginIn(Strict):
    email: Email
    password: Annoted[str, StringConstraints(min_length=1, max_length= 128)]

    