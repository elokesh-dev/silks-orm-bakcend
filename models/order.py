from mongoengine import (
    Document, EmbeddedDocument, StringField, FloatField,
    IntField, ListField, EmbeddedDocumentField, ReferenceField,
    BooleanField, DateTimeField
)
from datetime import datetime


class SareeItem(EmbeddedDocument):
    saree_type = StringField(required=True)
    price = FloatField()
    quantity = IntField(required=True, min_value=1)


class SareeDispatch(EmbeddedDocument):
    saree_type = StringField(required=True)
    quantity = IntField(required=True, min_value=1)


class VendorDispatch(EmbeddedDocument):
    """One send to one vendor for one process step."""
    id = StringField()                   # manual uuid so frontend can reference it
    vendor_id = StringField(required=True)
    vendor_name = StringField(required=True)
    sarees_sent = ListField(EmbeddedDocumentField(SareeDispatch))
    status = StringField(default="in_process", choices=["in_process", "completed"])
    price = FloatField()
    logistics_vendor = StringField()
    logistics_type = StringField()
    sent_at = DateTimeField()
    completed_at = DateTimeField()

    def to_dict(self):
        return {
            "id": self.id or "",
            "vendor_id": self.vendor_id,
            "vendor_name": self.vendor_name,
            "sarees_sent": [
                {"saree_type": s.saree_type, "quantity": s.quantity}
                for s in (self.sarees_sent or [])
            ],
            "status": self.status,
            "price": self.price,
            "logistics_vendor": self.logistics_vendor or "",
            "logistics_type": self.logistics_type or "",
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class Order(Document):
    client = ReferenceField("Client", required=True)
    client_name = StringField(required=True)

    order_type = StringField(
        required=True,
        choices=["call", "whatsapp", "store_visit", "reference"]
    )
    reference_name = StringField()
    sarees = ListField(EmbeddedDocumentField(SareeItem))

    status = StringField(
        default="order_pending",
        choices=["order_pending", "packing_completed", "completed"]
    )

    # Each is now a list of VendorDispatch
    gum = ListField(EmbeddedDocumentField(VendorDispatch), default=list)
    polishing = ListField(EmbeddedDocumentField(VendorDispatch), default=list)
    blouse_work = ListField(EmbeddedDocumentField(VendorDispatch), default=list)

    invoice_number = StringField()
    remarks = StringField()
    is_locked = BooleanField(default=False)

    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    meta = {"collection": "orders"}

    def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        return super().save(*args, **kwargs)

    def _step_status(self, dispatches):
        """Derived status for a process step based on its dispatches."""
        if not dispatches:
            return "pending"
        if all(d.status == "completed" for d in dispatches):
            return "completed"
        return "in_process"

    def to_dict(self):
        return {
            "id": str(self.id),
            "client_id": str(self.client.id) if self.client else "",
            "client_name": self.client_name,
            "order_type": self.order_type,
            "reference_name": self.reference_name or "",
            "sarees": [
                {"saree_type": s.saree_type, "price": s.price, "quantity": s.quantity}
                for s in (self.sarees or [])
            ],
            "status": self.status,
            "gum": [d.to_dict() for d in self.gum],
            "gum_status": self._step_status(self.gum),
            "polishing": [d.to_dict() for d in self.polishing],
            "polishing_status": self._step_status(self.polishing),
            "blouse_work": [d.to_dict() for d in self.blouse_work],
            "blouse_work_status": self._step_status(self.blouse_work),
            "invoice_number": self.invoice_number or "",
            "remarks": self.remarks or "",
            "is_locked": self.is_locked,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }