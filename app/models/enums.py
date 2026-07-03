import enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    DISPATCHER = "dispatcher"
    DRIVER = "driver"
    CUSTOMER = "customer"


class VehicleStatus(str, enum.Enum):
    AVAILABLE = "available"
    IN_USE = "in_use"
    MAINTENANCE = "maintenance"


class ShipmentStatus(str, enum.Enum):
    CREATED = "created"
    ASSIGNED = "assigned"
    PICKED_UP = "picked_up"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


# Allowed forward transitions for a shipment's lifecycle.
SHIPMENT_TRANSITIONS: dict[ShipmentStatus, set[ShipmentStatus]] = {
    ShipmentStatus.CREATED: {ShipmentStatus.ASSIGNED, ShipmentStatus.CANCELLED},
    ShipmentStatus.ASSIGNED: {ShipmentStatus.PICKED_UP, ShipmentStatus.CANCELLED},
    ShipmentStatus.PICKED_UP: {ShipmentStatus.IN_TRANSIT, ShipmentStatus.CANCELLED},
    ShipmentStatus.IN_TRANSIT: {
        ShipmentStatus.OUT_FOR_DELIVERY,
        ShipmentStatus.CANCELLED,
    },
    ShipmentStatus.OUT_FOR_DELIVERY: {ShipmentStatus.DELIVERED},
    ShipmentStatus.DELIVERED: set(),
    ShipmentStatus.CANCELLED: set(),
}
