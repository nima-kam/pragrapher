import copy
import pickle
import pprint
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, List, Optional, Set, Tuple, Union
from relmgr._core import _CoreRelationshipManager


class _EnforcingRelationshipManager(_CoreRelationshipManager):
    """
    A stricter Relationship Manager which adds the method 'enforce'
    where you register the cardinality and directionality of each relationship.

    Benefits:

        - When adding and removing relationships, bi directional relationships 
        are automatically created. (though remember, back pointer queries are 
        also always possible in the case of regular RelationshipManager, I think
        this is more of an official wiring rather than using a back pointer concept?)

        - When adding the same relationship again (by mistake?) any previous 
        relationship is removed first.

    Parameters:
    
        cardinality:
            - "onetoone" - extinguish both old 'source' and 'target' before adding a new relationship
            - "onetomany" - extinguish old 'source' before adding a new relationship
            - "manytomany" (not implemented)

        directionality:
            - "directional" - the default, no special enforcement
            - "bidirectional" - when calling `RelationshipManager.add_rel(source, target)`
            causes not only the primary relationship to be created between 'source' and 'target',
            but also auto creates an additional relationship in the reverse direction between 'target' and 'source'.
            Also ensures both relationships are removed when calling `RelationshipManager.remove_rel`.        
    """

    def __init__(self):
        super().__init__()
        self.rules: Dict[any, Tuple] = {}

    def enforce(self, relId, cardinality, directionality="directional"):
        self.rules[relId] = (cardinality, directionality)

    def _remove_existing_relationships(self, source, target, rel_id):
        def _extinguish_old_source():
            old_source = self._find_object(None, target, rel_id)  # find_source
            self.remove_rel(old_source, target, rel_id)

        def _extinguish_old_target():
            old_target = self._find_object(source, None, rel_id)  # find_target
            self.remove_rel(source, old_target, rel_id)
        if rel_id in list(self.rules.keys()):
            cardinality, directionality = self.rules[rel_id]
            if cardinality == "onetoone":
                _extinguish_old_source()
                _extinguish_old_target()
            elif cardinality == "onetomany":  # and directionality == "directional":
                _extinguish_old_source()

    def add_rel(self, fromObj, toObj, relId=1):
        self._remove_existing_relationships(fromObj, toObj, relId)
        super().add_rel(fromObj, toObj, relId)
        if relId in list(self.rules.keys()):
            cardinality, directionality = self.rules[relId]
            if directionality == "bidirectional":
                super().add_rel(toObj, fromObj, relId)

    def remove_rel(self, fromObj, toObj, relId=1):
        super().remove_rel(fromObj, toObj, relId)
        if relId in list(self.rules.keys()):
            cardinality, directionality = self.rules[relId]
            if directionality == "bidirectional":
                super().remove_rel(toObj, fromObj, relId)

    def clear(self) -> None:
        super().clear()
        self.rules = {}
