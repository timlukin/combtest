#-*- coding: utf-8 -*-
import itertools as it

class Slot (tuple):
    '''Slot is an immutable tuple of values for SlotScheme object. 
It's organized as tuple, because there are lots of them to save, and they are short, so, linear access is rather effective.
Slot also has a state: 'uncovered', 'covered' or 'excluded'. This state is related to current generation process.
'''
    states = ('uncovered', 'covered', 'excluded', 'optional')

    def __new__ (cls, vals, slot_scheme, single_scheme_slot_suite=None):
        if not isinstance(vals, (tuple, dict)):
            raise TypeError("`vals` argument must be either tuple or dict, but it is %s" % type(vals))
        if len(vals) != len(slot_scheme):
            raise RuntimeError("`vals` length must be equal to %d (due to slot scheme length")
        if isinstance(vals, dict):
            vals = tuple([vals[k] for k in SlotScheme])
        obj = tuple.__new__(cls, vals)
        obj.slot_scheme = slot_scheme
        obj.single_scheme_slot_suite = single_scheme_slot_suite
        obj.state = None
        obj.mark_uncovered()
        return obj
        
    def __getitem__ (self, key):
        return super(Slot, self).__getitem__(self.slot_scheme.index(key))

    def _mark_not_uncovered_method (self, state):
        if not self.single_scheme_slot_suite is None \
           and self.is_uncovered():
            self.single_scheme_slot_suite.uncovered_count -= 1
        self.state = state

    def mark_uncovered (self):
        if not self.single_scheme_slot_suite is None \
           and not self.is_uncovered():
            self.single_scheme_slot_suite.uncovered_count += 1
        self.state = 0

    def mark_covered (self):
        return self._mark_not_uncovered_method(1)

    def mark_excluded (self):
        return self._mark_not_uncovered_method(2)

    def mark_optional (self):
        return self._mark_not_uncovered_method(3)
 
    def get_state (self):
        return self.__class__.states[self.state]
        
    def is_uncovered (self):
        return self.state == 0

    def is_covered (self):
        return self.state == 1

    def is_excluded (self):
        return self.state == 2

    def is_optional (self):
        return self.state == 3
        
#     @staticmethod
#     def flatten (tpl, flat_slot_scheme, nested_slot_scheme):
#         '''Returns is None if it is not possible to flatten it (there are contradiction in outer and inner objects)
#         CHECKS:
#         len(tpl) must be equal to len(nested_slot_scheme)
#         indexes of `Slot` instances in tpl are equal to indexes of `SlotScheme` instances in nested_slot_scheme
#         result keys must be the same set as flat_slot_scheme elements
# '''
#         result = {}
#         def add_value (par, val):
#             if dct.has_key(par) and dct[par] != val:
#                 return False
#             else:
#                 result[par] = val
#                 return True
#         for i in xrange(len(nested_slot_scheme)):
#             par = nested_slot_scheme[i]
#             val = tpl[i]
#             if isinstance(val, Slot):
#                 for j in xrange(len (Slot)):
#                     par = par[j]
#                     val = val[j]
#                     if not add_value(par, val): return None 
#             else:
#                 if not add_value(par, val): return None
#         return Slot(result, flat_slot_scheme)

class SlotScheme (tuple):
    '''SlotScheme is an immutable tuple of parameters names.'''
    def __new__ (cls, *args):
        if len(args) == 1 and hasattr(args[0], '__iter__'):
            args = args[0]
        return tuple.__new__(cls, sorted(args))

    # @staticmethod
    # def flatten (slot_scheme):
    #     for i in xrange(len(slot_scheme)):
    #         if isinstance(slot_scheme[i], SlotScheme):
    #             return scheme[:i] + slot_scheme[i] + flatten(slot_scheme[i+1:])
    #     return slot_scheme


class SingleSchemeSlotSuite (list):
    '''SingleSchemeSlotSuite is a suite with slots, that fit one SlotScheme.'''
    def __init__ (self, slot_scheme, slots=None, generate=False, model=None):
        self.slot_scheme = slot_scheme
#        self.slot_scheme = SlotScheme.flatten(slot_scheme)
        self.uncovered_count = 0
        if slots is None:
            if generate is True:
                slots = self.generate(model)
            else:
                slots = []
        else:
            slots = slots[:]
        map(lambda slot: slot.single_scheme_slot_suite == self, slots)
        super(SingleSchemeSlotSuite, self).__init__(slots)

    def generate (self, model):
        domains_list = []
        for par in self.slot_scheme:
            domains_list.append(model[par])
        result = []
        # take cartesian product of domains list and flatten them
        for slot in it.product(*domains_list):
            result.append(Slot(slot, self.slot_scheme))
        for slot in result:
            if not model.fits_optional_constraints(slot):
                slot.mark_optional()
            if not model.fits_mandatory_constraints(slot):
                slot.mark_excluded()
        return result

    def get_uncovered (self):
        return filter(lambda slot: slots.is_uncovered(), self)
    

class MultiSchemeSlotSuite (dict):
    '''MultiSchemeSlotSuite is a dict of `SingleSchemeSlotSuite` objects'''
    def __init__ (self, slot_schemes, generate=False, model=None):
        super(MultiSchemeSlotSuite, self).__init__([
            (slot_scheme, SingleSchemeSlotSuite(slot_scheme,
                                                generate=generate,
                                                model=model)) 
            for slot_scheme in slot_schemes])

    def uncovered_count (self):
        return sum(map(lambda slot_scheme: slot_scheme.uncovered_count(), self))


