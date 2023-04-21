"""
Relationship manager.
(c) Andy Bulka 2003-2020 (wow that's a long time!)
https://github.com/abulka/relationship-manager

  ____      _       _   _                 _     _
 |  _ \ ___| | __ _| |_(_) ___  _ __  ___| |__ (_)_ __
 | |_) / _ \ |/ _` | __| |/ _ \| '_ \/ __| '_ \| | '_ \
 |  _ <  __/ | (_| | |_| | (_) | | | \__ \ | | | | |_) |
 |_| \_\___|_|\__,_|\__|_|\___/|_| |_|___/_| |_|_| .__/
                                                 |_|
  __  __
 |  \/  | __ _ _ __   __ _  __ _  ___ _ __
 | |\/| |/ _` | '_ \ / _` |/ _` |/ _ \ '__|
 | |  | | (_| | | | | (_| | (_| |  __/ |
 |_|  |_|\__,_|_| |_|\__,_|\__, |\___|_|
                           |___/
"""
from typing import List, Set, Dict, Tuple, Optional, Union
import pickle
from dataclasses import dataclass  # requires at least 3.7
import copy


class EfficientRelationshipManager(object):
    """
    Good core implementation, maps forward and reverse pointers
    for efficiency e.g.

        relations {
            from1 : {to1:[rel1]}
            from2 : {to5:[rel1,rel2], to6:[rel1]}
        }
        inverseRelations {
            same as above except meaning is reversed.
        }

    Adds Relationships property for setting and getting the relationships
    which helps if persisting.

    core - for older core versions see misc/old orginal/
    """

    def __init__(self):     # Constructor
        self.Relations = {}
        self.InverseOfRelations = {}

    def GetRelations(self):
        result = []
        for fromobj in self.Relations:
            todict = self.Relations[fromobj]
            for toobj in todict:
                for relId in todict[toobj]:
                    result.append((fromobj, toobj, relId))
        return result

    def SetRelations(self, listofrelationshiptuples):
        for r in listofrelationshiptuples:
            self.AddRelationship(From=r[0], To=r[1], RelId=r[2])
    Relationships = property(GetRelations, SetRelations)  # ANDY

    def AddRelationship(self, From, To, RelId=1):
        def AddEntry(relationsDict, From, To, RelId):
            if From not in relationsDict:
                relationsDict[From] = {}
            if To not in relationsDict[From]:
                relationsDict[From][To] = []
            if RelId not in relationsDict[From][To]:
                relationsDict[From][To].append(RelId)
        AddEntry(self.Relations, From, To, RelId)
        AddEntry(self.InverseOfRelations, To, From, RelId)

    def RemoveRelationships(self, From, To, RelId=1):
        """
        Specifying None as a parameter means 'any'
        """
        def havespecifiedallParams(): return (
            From != None and To != None and RelId != None)

        def NumberOfNonWildcardParamsSupplied():
            numberOfNoneParams = 0
            if From == None:
                numberOfNoneParams += 1
            if To == None:
                numberOfNoneParams += 1
            if RelId == None:
                numberOfNoneParams += 1
            return numberOfNoneParams

        if NumberOfNonWildcardParamsSupplied() > 1:
            raise RuntimeError(
                'Only one parameter can be left as None, (indicating a match with anything).')

        def ZapRelId(From, To, RelId):
            def _ZapRelationId(rdict, From, To, RelId):
                assert (From != None and To != None and RelId != None)
                relList = rdict[From][To]
                if RelId in relList:
                    relList.remove(RelId)
                if relList == []:     # no more relationships, so remove the entire mapping
                    del rdict[From][To]
            _ZapRelationId(self.Relations,          From, To,   RelId)
            _ZapRelationId(self.InverseOfRelations, To,   From, RelId)

        if havespecifiedallParams():
            if self.FindObjects(From, To, RelId):  # returns T/F
                ZapRelId(From, To, RelId)
        else:
            # this list will be either From or To or RelIds depending on which param was set as None (meaning match anything)
            lzt = self.FindObjects(From, To, RelId)
            if lzt:
                for objOrRelid in lzt:
                    if From == None:
                        # lzt contains all the things that point to 'To' with relid 'RelId'
                        # objOrRelid is the specific thing during this iteration that point to 'To', so delete it
                        ZapRelId(objOrRelid, To, RelId)
                    elif To == None:
                        ZapRelId(From, objOrRelid, RelId)
                    elif RelId == None:
                        ZapRelId(From, To, objOrRelid)

    def FindObjects(self, From=None, To=None, RelId=1):
        """
        Specifying None as a parameter means 'any'
        Can specify
          # 'From' is None - use normal relations dictionary
          From=None To=blah RelId=blah  anyone pointing to 'To' of specific RelId
          From=None To=blah RelId=None  anyone pointing to 'To'

          # 'To' is None - use inverse relations dictionary
          From=blah To=None RelId=blah  anyone 'From' points to, of specific RelId
          From=blah To=None RelId=None  anyone 'From' points to

          # Both 'To' & 'From' specified, use any e.g. use normal relations dictionary
          From=blah To=blah RelId=None  all RelId's between blah and blah
          From=blah To=blah RelId=blah  T/F does this specific relationship exist

          From=None To=None RelId=blah  error (though you could implement returning a list of From,To pairs using the R blah e.g. [('a','b'),('a','c')]
          From=None To=None RelId=None  error
        """
        if From == None and To == None:
            raise RuntimeError("Either 'From' or 'To' has to be specified")

        def havespecifiedallParams(): return (
            From != None and To != None and RelId != None)
        resultlist = []

        if From == None:
            subdict = self.InverseOfRelations.get(To, {})
            resultlist = [k for k, v in subdict.items() if (
                RelId in v or RelId == None)]

        elif To == None:
            # returns a list of all the matching tos
            subdict = self.Relations.get(From, {})
            resultlist = [k for k, v in subdict.items() if (
                RelId in v or RelId == None)]

        else:
            """
            # Both 'To' & 'From' specified, use any e.g. use normal relations dictionary
            From=blah To=blah RelId=None  all RelId's between blah and blah
            From=blah To=blah RelId=blah  T/F does this specific relationship exist
            """
            subdict = self.Relations.get(From, {})
            relationIdsList = subdict.get(To, [])
            if RelId == None:
                # return the entire list of relationship ids between these two.
                resultlist = relationIdsList
            else:
                return RelId in relationIdsList  # return T/F
        return copy.copy(resultlist)

    def Clear(self):
        self.Relations.clear()
        self.InverseOfRelations.clear()

    def FindObject(self, From=None, To=None, RelId=1):    # ANDY
        lzt = self.FindObjects(From, To, RelId)
        if lzt:
            return lzt[0]
        else:
            return None


class RMCoreImplementation(EfficientRelationshipManager):
    pass


class BasicRelationshipManager:
    """
    Could use a different core api implementation, though GetRelations() and SetRelations()
    only supported by the later core implementations in misc/old original/.
    """

    def __init__(self) -> None:
        self.rm = RMCoreImplementation()

    def GetRelations(self) -> List[Tuple[object, object, Union[int, str]]]:
        return self.rm.GetRelations()

    def SetRelations(self, listofrelationshiptuples: List[Tuple[object, object, Union[int, str]]]) -> None:
        self.rm.SetRelations(listofrelationshiptuples)

    Relationships = property(GetRelations, SetRelations)

    def AddRelationship(self, From, To, RelId=1) -> None:
        self.rm.AddRelationship(From, To, RelId)

    def RemoveRelationships(self, From, To, RelId=1) -> None:
        self.rm.RemoveRelationships(From, To, RelId)

    def FindObjects(self, From=None, To=None, RelId=1) -> Union[List[object], bool]:
        return self.rm.FindObjects(From, To, RelId)

    def FindObject(self, From=None, To=None, RelId=1) -> object:
        return self.rm.FindObject(From, To, RelId)

    def FindObjectPointedToByMe(self, fromObj, relId=1) -> object:
        return self.rm.FindObject(fromObj, None, relId)

    def FindObjectPointingToMe(self, toObj, relId=1) -> object:  # Back pointer query
        return self.rm.FindObject(None, toObj, relId)

    def Clear(self) -> None:
        self.rm.Clear()


class EnforcingRelationshipManager(BasicRelationshipManager):
    """
    A stricter Relationship Manager which adds the method 'EnforceRelationship'
    where you register the cardinality and directionality of each relationship.

    Benefits:

        - When adding and removing relationships, bi directional relationships 
        are automatically created. (though remember, back pointer queries are 
        also always possible in the case of regular RelationshipManager, I think
        this is more of an official wiring rather than using a back pointer concept?)

        - When adding the same relationship again (by mistake?) any previous 
        relationship is removed first.
    """

    def __init__(self):
        super().__init__()
        self.enforcer = {}

    def EnforceRelationship(self, relId, cardinality, directionality="directional"):
        self.enforcer[relId] = (cardinality, directionality)

    def _RemoveExistingRelationships(self, fromObj, toObj, relId):
        def ExtinguishOldFrom():
            oldFrom = self.FindObjectPointingToMe(toObj, relId)
            self.RemoveRelationships(oldFrom, toObj, relId)

        def ExtinguishOldTo():
            oldTo = self.FindObjectPointedToByMe(fromObj, relId)
            self.RemoveRelationships(fromObj, oldTo, relId)
        if relId in list(self.enforcer.keys()):
            cardinality, directionality = self.enforcer[relId]
            if cardinality == "onetoone":
                ExtinguishOldFrom()
                ExtinguishOldTo()
            elif cardinality == "onetomany":  # and directionality == "directional":
                ExtinguishOldFrom()

    def AddRelationship(self, fromObj, toObj, relId=1):
        self._RemoveExistingRelationships(fromObj, toObj, relId)
        super().AddRelationship(fromObj, toObj, relId)
        if relId in list(self.enforcer.keys()):
            cardinality, directionality = self.enforcer[relId]
            if directionality == "bidirectional":
                self.rm.AddRelationship(toObj, fromObj, relId)

    def RemoveRelationships(self, fromObj, toObj, relId=1):
        super().RemoveRelationships(fromObj, toObj, relId)
        if relId in list(self.enforcer.keys()):
            cardinality, directionality = self.enforcer[relId]
            if directionality == "bidirectional":
                self.rm.RemoveRelationships(toObj, fromObj, relId)

    def Clear(self) -> None:
        super().Clear()
        self.enforcer = {}

    # Add short API for pithy, more convenient unit testing

    def ER(self, relId, cardinality, directionality="directional"):
        self.EnforceRelationship(relId, cardinality, directionality)

    def R(self, fromObj, toObj, relId=1):
        self.AddRelationship(fromObj, toObj, relId)

    def P(self, fromObj, relId=1):
        # findObjectPointedToByMe(fromMe, id, cast)
        return self.FindObject(fromObj, None, relId)

    def B(self, toObj, relId=1):
        # findObjectPointingToMe(toMe, id cast)
        return self.FindObject(None, toObj, relId)

    def PS(self, fromObj, relId=1):
        # findObjectsPointedToByMe(fromMe, id, cast)
        return self.FindObjects(fromObj, None, relId)

    def NR(self, fromObj, toObj, relId=1):
        self.RemoveRelationships(fromObj, toObj, relId)    

    def CL(self):
        self.Clear()


# Persistence


@dataclass
class Namespace:
    """Just want a namespace to store vars/attrs in. Could use a dictionary."""


@dataclass
class PersistenceWrapper:
    """Holds both objects and relationships. Could use a dictionary."""
    objects: Namespace  # Put all your objects involved in relationships as attributes of this object
    relations: List  # Relationship Manager relationship List will go here


class RelationshipManagerPersistent(EnforcingRelationshipManager):
    """
    Persistent Relationship Manager.  

    Provides an attribute object called `.objects` where you can keep all the
    objects involved in relationships e.g.

        rm.objects.obj1 = Entity(strength=1, wise=True, experience=80)

    Then when you persist the Relationship Manager both the objects and
    relations are pickled and later restored. This means your objects are
    accessible by attribute name e.g. rm.objects.obj1 at all times. You can
    assign these references to local variables for convenience e.g.

        obj1 = rm.objects.obj1

    Usage:
        # persist
        asbytes = rm.dumps()

        # resurrect
        rm2 = RelationshipManagerPersistent.loads(asbytes)
    """

    def __init__(self):
        super().__init__()
        self.objects = Namespace()  # assign to this namespace directly to record your objects

    def Clear(self):
        super().__init__()
        self.objects = Namespace()

    def dumps(self) -> bytes:
        return pickle.dumps(PersistenceWrapper(
            objects=self.objects, relations=self.Relationships))

    @staticmethod
    def loads(asbytes: bytes):  # -> RelationshipManagerPersistent:
        data: PersistenceWrapper = pickle.loads(asbytes)
        rm = EnforcingRelationshipManager()
        rm.objects = data.objects
        rm.Relationships = data.relations
        return rm


class RelationshipManager(RelationshipManagerPersistent):
    """Main Relationship Manager to use in your projects."""
