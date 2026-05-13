import copy
import pickle
import pprint
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, List, Optional, Set, Tuple, Union


class _CoreRelationshipManager(object):
    """
    Good efficient implementation in that it maps forward and reverse pointers
    for better performance of backpointer lookups e.g.

        relations {
            from1 : {to1:[rel1]}
            from2 : {to5:[rel1,rel2], to6:[rel1]}
        }
        inverseRelations {
            same as above except meaning is reversed.
        }

    Has relationships property for setting and getting the relationships
    which helps if persisting.

    """

    def __init__(self):
        self.relations: Dict = {}
        self.inverse_relations: Dict = {}

    def _get_relationships(self) -> List[Tuple[object, object, Union[int, str]]]:
        result = []
        for source in self.relations:
            to_dict = self.relations[source]
            for target in to_dict:
                for rel_id in to_dict[target]:
                    result.append((source, target, rel_id))
        return result

    def _set_relationships(self, list_of_relationship_tuples: List[Tuple[object, object, Union[int, str]]]):
        for r in list_of_relationship_tuples:
            self.add_rel(source=r[0], target=r[1], rel_id=r[2])
    relationships = property(_get_relationships, _set_relationships)

    def add_rel(self, source, target, rel_id=1) -> None:
        def _add_entry(relations: Dict, source, target, rel_id):
            if source not in relations:
                relations[source] = {}
            if target not in relations[source]:
                relations[source][target] = []
            if rel_id not in relations[source][target]:
                relations[source][target].append(rel_id)
        _add_entry(self.relations, source, target, rel_id)
        _add_entry(self.inverse_relations, target, source, rel_id)

    def remove_rel(self, source, target, rel_id=1) -> None:
        """
        Specifying None as a parameter means 'any'
        """
        def _have_specified_all_params(): return (
                source is not None and target is not None and rel_id is not None)

        def _number_of_wildcard_params():
            result = 0  # number of None params, which represent a wildcard match
            if source is None:
                result += 1
            if target is None:
                result += 1
            if rel_id is None:
                result += 1
            return result

        if _number_of_wildcard_params() > 1:
            raise RuntimeError(
                'Only one parameter can be left as None, (indicating a match with anything).')

        def _zap_relationship(source, target, rel_id):
            def _zap_rel_id(rdict, source, target, rel_id):
                assert (source is not None and target is not None and rel_id is not None)
                rel_list = rdict[source][target]
                if rel_id in rel_list:
                    rel_list.remove(rel_id)
                if not rel_list:     # no more relationships, so remove the entire mapping
                    del rdict[source][target]
            _zap_rel_id(self.relations,          source, target,   rel_id)
            _zap_rel_id(self.inverse_relations, target,   source, rel_id)

        if _have_specified_all_params():
            if self._find_objects(source, target, rel_id):  # returns T/F
                _zap_relationship(source, target, rel_id)
        else:
            # this list will be either 'source' or 'target' or RelIds depending on which param was set as None (meaning match anything)
            lzt = self._find_objects(source, target, rel_id)
            if lzt:
                for it in lzt:  # strangely, 'it' is an object or rel_id
                    if source == None:
                        # lzt contains all the things that point to 'target' with relid 'rel_id'
                        # 'it' is the specific thing during this iteration that point to 'target', so delete it
                        _zap_relationship(it, target, rel_id)
                    elif target == None:
                        _zap_relationship(source, it, rel_id)
                    elif rel_id == None:
                        _zap_relationship(source, target, it)

    def _find_objects(self, source=None, target=None, rel_id=1) -> Union[List[object], bool]:
        """
        Low Level API method for querying. 

        Specifying None as a parameter means 'any' viz. the thing you are looking for.

        E.g. when you specify:
          # 'source' is None - use normal relations dictionary
          source=None target=blah rel_id=blah  anyone pointing to 'target' of specific rel_id
          source=None target=blah rel_id=None  anyone pointing to 'target'

          # 'target' is None - use inverse relations dictionary
          source=blah target=None rel_id=blah  anyone 'source' points to, of specific rel_id
          source=blah target=None rel_id=None  anyone 'source' points to

          # When specify both sides of a relationship, PLUS the relationship itself,
          # then there is nothing to find, so return a boolean T/F if that relationship exists.
          # Both 'target' & 'source' specified, use any e.g. use normal relations dictionary
          source=blah target=blah rel_id=None  all rel_id's between blah and blah
          source=blah target=blah rel_id=blah  T/F does this specific relationship exist

          # All none
          source=None target=None rel_id=blah  error (though you could implement returning a list of source,target pairs using the R blah e.g. [('a','b'),('a','c')]
          source=None target=None rel_id=None  error
        
        Tip: Other uses of None as a parameter value
            remove_rel(self, From, To, RelId=1) -> None: Specifying None as a parameter means 'any'
        """
        if source is None and target is None:
            raise RuntimeError("Either 'source' or 'target' has to be specified")

        def havespecifiedallParams(): return (
            source != None and target != None and rel_id != None)
        resultlist = []

        if source == None:
            subdict = self.inverse_relations.get(target, {})
            resultlist = [k for k, v in subdict.items() if (
                rel_id in v or rel_id == None)]

        elif target == None:
            # returns a list of all the matching tos
            subdict = self.relations.get(source, {})
            resultlist = [k for k, v in subdict.items() if (
                rel_id in v or rel_id == None)]

        else:
            """
            # Both 'target' & 'source' specified, use any e.g. use normal relations dictionary
            source=blah target=blah rel_id=None  all rel_id's between blah and blah
            source=blah target=blah rel_id=blah  T/F does this specific relationship exist
            """
            subdict: Dict = self.relations.get(source, {})
            rel_ids: List = subdict.get(target, [])
            if rel_id == None:
                # return the entire list of relationship ids between these two.
                resultlist = rel_ids
            else:
                return rel_id in rel_ids  # return T/F
        return copy.copy(resultlist)

    def _find_object(self, source=None, target=None, rel_id=1) -> object:
        """Find first object - low level"""
        lzt = self._find_objects(source, target, rel_id)
        if lzt:
            return lzt[0]
        else:
            return None

    def clear(self):
        self.relations.clear()
        self.inverse_relations.clear()
