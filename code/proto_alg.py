#!/usr/bin/python
#-*- coding: utf-8 -*-
import re, yaml
from itertools import combinations
## !! Два вида ограничений: НЕЛЬЗЯ и НЕ НУЖНО
## ?? Как строить ограничения на слоты из обычных констрэйнтов?
## !! Отдельно сделать для невалидных значений
## !! Отдельно - ожидаемый результат
## !! Отдельно - перегенерация на разных сидах до лучшего результата

# нужны параметры, домены параметров, комбинаторные правила и ограничения, чтобы сразу выбросить негодные комбинации (и заодно сократить количество ограничений). ТУТ КЛЮЧИ - МН-ВА ПАРАМЕТРОВ

# Заранее заданные тестовые случаи (не обязательно все параметры заполнены.

## !! Нужно не забыть, что первая же комбинация из сидов может покрыть и другие сиды !! Нужно вычеркивать поюзанные сиды после генерации тесткейса.

class TestSuite (list):
    def generate_nwise (self, model, seeds=[]):
        self.model = model
        logging.debug("Starting test suite generation with model\n%s." % model)
        self.params = model.params
        self.slots = SlotSuite(model)
        logging.debug("Slots to fill\n%s" % self.slots)
        self.constraints = ConstraintSuite(model)
        logging.debug("Found constraints\n%s" % self.constraints)
        seeds = self.get_seeds(seeds, constraints)
        self.seeds = seeds
        logging.debug("Found seeds\n%s." % "\n".join(map(str, self.seeds)))
        for s in self.seeds:
            self.slots.mark_slots_covered(s)
        logging.debug("Slots after seeds invasion\n%s" % self.slots)
        while slots.vacant_slots:
            self.add_test_case()
        logging.debug("Generated test suite\n%s" % self)

    def add_test_case (self):
        test_case = TestCase(self.model)
        if self.seeds:
            test_case.add(self.seeds.pop())
        while not test_case.is_full():
            cur_slot = None
            if test_case.is_empty():
                cur_slot = self.slots.get_most_uncovered_slot() # плохое название: здесь слот - значение, а наиболее непокрытый - вид слотов
            else:
                uncovered_params = test_case.get_uncovered_params()
                # находим все подходящие тест-кейсу слоты, покрывающие хотя бы один его непокрытый параметр
                slot_candidates = filter(lambda s: test_case.fits(s, self.constraints),
                                    reduce(lambda res, slots:
                                           res + slots.get_slots_for_param(),
                                           uncovered_params, []))
                if not slot_candidates:
                    raise PoorModelException("Failed to find slot, fitting test case %s with constraints %s" % (test_case, self.constraints))
                slot_candidates.sort(
                    lambda x, y: cmp(test_case.covering_index(x),
                                     test_case.covering_index(y)) \
                              or cmp(self.slots.priority(x),
                                     self.slots.priority(y)))
                cur_slot = slot_candidates[0]
            test_case.add(cur_slot)
            slots.mark_slots_covered(test_case)
        self.append(test_case)

    def get_seeds (self, init_seeds, constraints, param=None):
        '''Get some initial Seeds (sub-testcases) for generation. Can generate with param or in a random way. Looking for constrain'''
        return init_seeds

class TestCase (dict):
    def __init__ (self, model, data={}):
        super(TestCase, self).__init__(data)
        self.model = model # ссылка на модель 
        self.params = model.params
        self.size = len(params)
        self.fullness = len(self)

    def is_empty (self):
        return self.fullness == 0

    def is_full (self):
        return self.fullness == self.size

    def add (self, data):
        # считаем, что Seed-ами наполняемся так же, как dict-ом.
        super(TestCase, self).update(data)

    def get_uncovered_params (self):
        pass
                                    
    def fits (self, slot, constraints=None):
        pass

    def covering_index (self, slot):
        pass

class Seed (dict):
    pass
        

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
        raw_model = yaml.load(yaml_model)
        self.data = self._normalize_data(raw_model["data"])
        self.params = self.data.keys()
        self.constraints = {}
        if raw_model["constraints"]:
            for k in ["optional", "mandatory"]:
                self.constraints[k] = self._parse_constraints(raw_model["constraints"].get(k, []))
        self.scheme = raw_model["scheme"]
        # if len(self.scheme.keys()) > 1:
        #     self.scheme = { "_1": self.scheme }
        self.priority = self._normalize_priority(raw_model["priority"])

        
    def _normalize_data (self, data):
        for k, v in data.items():
            if isinstance(v, list):
                pass
            elif isinstance(v, dict):
                for kk, vv in self._normalize_data(v).iteritems():
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
                for kk, vv in self._normalize_priority(v).iteritems():
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
        
        
class SlotSuite (object):
    valency_re = re.compile("_+(\d+)")
    def __init__ (self, model):
        self.model = model
        scheme = model.scheme
        self.slots = self._gen_slots(scheme)
        logging.debug("Generated slots suite:\n%s" % self)
        self.vacant_slots = sum(map(lambda s: s.vacant_slots, self.slots))

    def _gen_slots (self, scheme):
        result = {} # { (sorted p1, p2, p3): [(v1, v2, v3), ...], ... }
        valency = scheme.keys()[0]
        params = scheme.values()[0]
        p = len(params)

        # заполнить { par1 => [val1, ...], '_sm2' => {result struct} }
        param_dct = {}
        for i in xrange(p):
            par = params[i]
            if isinstance(par, dict):
                par_name = "_sm%d" % i
                params[i] = par_name
                param_dct[par_name] = self._gen_slots(scheme=par)
            else:
                param_dct[par] = model["data"][par]

        def get_next_val(par):
            next(par)
        # теперь перебираем комбинации
        for comb in combinations(p, valency):
            pars_comb = map(params.__getitem__, comb) # содержит _sm%d - подмодели со словарями
            pars_line = []
            for pars in 




        # теперь в param_dct должны лежать параметр: значения, причем некоторые параметры - отсортированные кортежи
        # нужно в result положить (отсортированный кортеж параметров: значение), раскрывая кортежи из param_dct и подвергая их сортировке с остальными
                

    def mark_slots_covered (self, seed_or_test_case):
        pass

    def get_most_uncovered_slot (self):
        pass

    def get_slots_for_param (self):
        pass

    def priority(self):
        pass


class Slot (dict):
    def fits_another_slot (self, slot):
        pass


class ConstraintSuite (SlotSuite):
    pass

class PoorModelException (Exception):
    pass

if __name__ == '__main__':
    model = Model(Model.__doc__)
    print "..."
    print yaml.dump(model.constraints, default_flow_style=False)
