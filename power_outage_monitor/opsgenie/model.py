from typing import List

from pydantic import BaseModel, Field

class ExtraProperties(BaseModel):
    sensor_id: str = Field(alias='sensorId')
    group: str
    device: str

class ActionSource(BaseModel):
    type: str
    source: str

class Parameter(BaseModel):
    name: str
    type: str
    value: str

class Alert(BaseModel):
    count: str
    description: str
    extra_properties: ExtraProperties = Field(alias='extraProperties')
    source: str
    message: str
    priority: str
    tags: List[str] = []
    tiny_id: str = Field(alias='tinyId')
    alias: str
    id: str
    actions: List[str] = []
    entity: str
    status: str

class OpsgenieRequest(BaseModel):
    alert: Alert
    customer: str = Field(alias='customerName')
    timestamp: str
    action_source: ActionSource = Field(alias='actionSource')
    action_name: str = Field(alias='actionName')
