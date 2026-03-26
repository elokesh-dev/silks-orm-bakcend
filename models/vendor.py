from mongoengine import Document, StringField


class Vendor(Document):
    name = StringField(required=True)
    # process_type: gum | polishing | blouse_work
    process_type = StringField(required=True, choices=["gum", "polishing", "blouse_work"])
    phone = StringField()
    address = StringField()

    meta = {"collection": "vendors"}

    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "process_type": self.process_type,
            "phone": self.phone or "",
            "address": self.address or "",
        }
