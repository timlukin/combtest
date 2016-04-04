#!/usr/bin/python
#-*- coding: utf-8 -*-
import itertools as it

class Slot (tuple):
    '''Slot is an immutable tuple of values for SlotScheme object. 
It's organized as tuple, because there are lots of them to save, and they are short, so, linear access is rather effective.
Slot also has a state: 'uncovered', 'covered' or 'excluded'. This state is related to current generation process.
'''
    states = ('uncovered', 'covered', 'excluded', 'optional')

    def __init__ (self, vals, slot_scheme):
        if not isinstance(vals, tuple, dict):
            raise TypeError("`vals` argument must be either tuple or dict, but it is %s" % type(vals))
        if len(vals) != len(slot_scheme):
            raise RuntimeError("`vals` length must be equal to %d (due to slot scheme length")
        self.slot_scheme = slot_scheme
        if isinstance(vals, dict):
            vals = tuple([vals[k] for k in SlotScheme])
        super(Slot, self).__init__(vals)
        self.state = 0 # 'uncovered'
        self.single_scheme_slot_suite = None

    def __getitem__ (self, key):
        return self.vals[self.slot_scheme.index(key)]
        
    @staticmethod
    def flatten (tpl, flat_slot_scheme, nested_slot_scheme):
        '''Returns is None if it is not possible to flatten it (there are contradiction in outer and inner objects)
        CHECKS:
        len(tpl) must be equal to len(nested_slot_scheme)
        indexes of `Slot` instances in tpl are equal to indexes of `SlotScheme` instances in nested_slot_scheme
        result keys must be the same set as flat_slot_scheme elements
'''
        result = {}
        def add_value (par, val):
            if dct.has_key(par) and dct[par] != val:
                return False
            else:
                result[par] = val
                return True
        for i in xrange(len(nested_slot_scheme)):
            par = nested_slot_scheme[i]
            val = tpl[i]
            if isinstance(val, Slot):
                for j in xrange(len(Slot)):
                    par = par[j]
                    val = val[j]
                    return None if not add_value(par, val)
            else:
                return None if not add_value(par, val)
        return Slot(result, flat_slot_scheme)

    def mark_uncovered (self):
        self.state = 0
        if not self.single_scheme_slot_suite is None:
            self.single_scheme_slot_suite.uncovered_count += 1

    def mark_covered (self):
        self.state = 1
        if not self.single_scheme_slot_suite is None:
            self.single_scheme_slot_suite.uncovered_count -= 1

    def mark_excluded (self):
        self.state = 2
        if slot.is_uncovered() and not self.single_scheme_slot_suite is None:
            self.single_scheme_slot_suite.uncovered_count -= 1            

    def mark_optional (self):
        self.state = 3
        if slot.is_uncovered() and not self.single_scheme_slot_suite is None:
            self.single_scheme_slot_suite.uncovered_count -= 1           
 
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


class SlotScheme (tuple):
    '''SlotScheme is an immutable tuple of parameters names.'''
    def __init__ (self, *args):
        if len(args) == 1 and hasattr(args[0], '__iter__'):
            args = args[0]
        super(SlotScheme, self).__init__(sorted(args))

    @staticmethod
    def flatten (slot_scheme):
        for i in xrange(len(slot_scheme)):
            if isinstance(slot_scheme[i], SlotScheme):
                return scheme[:i] + slot_scheme[i] + flatten(slot_scheme[i+1:])
        return slot_scheme


class SingleSchemeSlotSuite (list):
    '''SingleSchemeSlotSuite is a suite with slots, that fit one SlotScheme.'''
    def __init__ (slot_scheme, slots=None, generate=False, model=None):
        self.nested_slot_scheme = slot_scheme
        self.slot_scheme = SlotScheme.flatten(slot_scheme)
        if slots is None:
            if generate is True:
                slots = self.generate(model)
            else:
                slots = []
        else:
            slots = slots[:]
        map(lambda slot: slot.single_scheme_slot_suite = self, slots)
        super(SingleSchemeSlotSuite, self).__init__(slots)
        self.uncovered_count = reduce(lambda res, slot: res + 1 if slot.is_uncovered() else 0, 
                                      self, 0)
 
    def generate (self, model):
        if not isinstance(model, Model):
            raise TypeError("SingleSchemeSlotSuite.generate needs `Model` argument")
        domains_list = []
        for par in self.nested_slot_scheme:
            domains_list.append(model[par])
        result = []
        # take cartesian product of domains list and flatten them
        for product_tuple in it.product(*domains_list)):
            flat_slot = Slot.flatten(product_tuple, self.slot_scheme, self.nested_slot_scheme) # can be None - see Slot.flatten doc
            if flat_slot is not None:
                result.append(flat_slot)
        for slot in result:
            if not model.fits_mandatory_constraints(slot):
                slot.mark_excluded()
            elif model.fits_optional_constraints(slot):
                slot.mark_optional()
        return result

    def get_uncovered (self):
        return filter(lambda slot: slots.is_uncovered(), self)
    
    def uncovered_count (self):
        return self.uncovered_count
    

class MultiSchemeSlotSuite (dict):
    '''MultiSchemeSlotSuite is a dict of `SingleSchemeSlotSuite` objects'''
    def __init__ (self, *slot_schemes, generate=False, model=None):
        super(MultiSchemeSlotSuite, self).__init__([
            (slot_scheme, SingleSchemeSlotSuite(slot_scheme,
                                                generate=generate,
                                                model=model)) 
            for slot_scheme in slot_schemes])

    def uncovered_count (self):
        return sum(map(lambda slot_scheme: slot_scheme.uncovered_count(), self))


class Model (object):
    '''
data:
    par1: [val11, val12]
    par2: val21
    par3:
      par3_1: [val311, val312]
      par3_2: [val321]
    par4: [val41, val42]
scheme:
    __2:
    - par3->par_3_1
    - par1
    - __3:
      - par3->par_3_2
      - par1
      - par2
constraints:
    optional:
      - "lambda par1, par2: par1 > par2"
      - "lambda par1, par2: par1 < par2 * 2"
    mandatory:
      - "lambda par2, par3, par1, par4: par1 != par3 or par2 != par3"
priority:
    par1:
      val12: 5
    par3:
      par3_1:
        val311: 10
'''
    sep = re.compile("\s*,\s*")
    lambda_signature_re = re.compile("^lambda\s+(.*)\s*:") # regexp for lambda arguments match
    def __init__ (self, yaml_model):
        def _normalize_data (self, data):
            for k, v in data.items():
                if isinstance(v, list):
                    pass
                elif isinstance(v, dict):
                    for kk, vv in _normalize_data(v).iteritems():
                        data["%s->%s" % (k, kk)] = vv
                    data.pop(k)
                else:
                    data[k] = [v]
            return data
        def _normalize_priority (self, priority):
            for k, v in priority.iteritems():
                if isinstance(v, dict):
                    if all(map(lambda x: isinstance(x, dict), v.values())):
                        sep = "%s->%s" 
                    else:
                        sep = "%s=%s"
                    for kk, vv in _normalize_priority(v).iteritems():
                        new_key = sep % (k, kk)
                        priority[new_key] = vv
                        priority.pop(k)
            return priority
        def _parse_constraints (self, constraints):
            parsed = {}
            for c_lambda in constraints:
                sig = ",".join(sorted(self.sep.split(self.lambda_signature_re.search(c_lambda).groups()[0])))
                if not parsed.has_key(sig):
                    parsed[sig] = []
                parsed[sig].append(eval(c_lambda))
            return parsed

        raw_model = yaml.load(yaml_model)
        self.data = _normalize_data(raw_model["data"])
        self.params = self.data.keys()
        self.constraints = {}
        if raw_model["constraints"]:
            for k in ["optional", "mandatory"]:
                self.constraints[k] = _parse_constraints(raw_model["constraints"].get(k, []))
        self.scheme = raw_model["scheme"]
        # if len(self.scheme.keys()) > 1:
        #     self.scheme = { "_1": self.scheme }
        self.priority = _normalize_priority(raw_model["priority"])
    
    def generate (self):
        
