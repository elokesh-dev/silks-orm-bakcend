from mongoengine import Document, StringField


class Client(Document):
    name = StringField(required=True)
    phone = StringField()
    address = StringField()

    meta = {"collection": "clients"}

    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "phone": self.phone or "",
            "address": self.address or "",
        }
