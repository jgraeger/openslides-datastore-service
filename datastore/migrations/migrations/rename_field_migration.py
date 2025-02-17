from typing import Any, Dict, List, Optional

from datastore.shared.util import collection_from_fqid

from .. import (
    BaseEvent,
    BaseMigration,
    CreateEvent,
    DeleteFieldsEvent,
    ListUpdateEvent,
    UpdateEvent,
)


class RenameFieldMigration(BaseMigration):
    """
    This migration renames a field from old_name to new_name for one collection.
    """

    collection: str
    old_field: str
    new_field: str

    def modify(self, object: Dict[str, Any]) -> None:
        if self.old_field in object:
            object[self.new_field] = object[self.old_field]
            del object[self.old_field]

    def migrate_event(
        self,
        event: BaseEvent,
    ) -> Optional[List[BaseEvent]]:
        collection = collection_from_fqid(event.fqid)
        if collection != self.collection:
            return None

        if isinstance(event, CreateEvent) or isinstance(event, UpdateEvent):
            self.modify(event.data)

        elif isinstance(event, DeleteFieldsEvent):
            if self.old_field in event.data:
                event.data.remove(self.old_field)
                event.data.append(self.new_field)

        elif isinstance(event, ListUpdateEvent):
            self.modify(event.add)
            self.modify(event.remove)

        return [event]
