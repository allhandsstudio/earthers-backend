from xml.etree.cElementTree import iterparse
import sys
import csv


class XmlDictConfig(dict):
    def __init__(self, parent_element):
        self['__attrib'] = parent_element.attrib
        self['__tag'] = parent_element.tag
        if parent_element.text:
            self['__text'] = parent_element.text.strip()
        else:
            self['__text'] = None
        for element in parent_element:
            if element.tag not in self:
                self[element.tag] = []
            self[element.tag].append(XmlDictConfig(element))


def parse(filename, run_id):
    doc = iterparse(filename, ('start', 'end'))
    
    is_sector = False
    is_resource = False
    is_final_demand = False

    region_name = ''
    sector_name = ''
    subsector_name = ''
    technology_name = ''
    period_year = ''
    is_stub = False
    is_transportation = False
    is_ag = False
    in_database = False
    in_consumer = False

    region_elem = None

    # CSV writers
    price_csv = open('price.csv', 'wb')
    price_writer = csv.writer(price_csv)
    price_writer.writerow(
        ['run_id', 'region', 'price_item', 'price_type', 'year', 'value'])
    
    subsector_shareweight_csv = open('subsector_shareweight.csv', 'wb')
    subsector_shareweight_writer = csv.writer(subsector_shareweight_csv)
    subsector_shareweight_writer.writerow(
        ['run_id', 'region', 'sector', 'subsector', 'is_transportation', 'is_agriculture', 'year', 'value'])
    
    period_csv = open('period.csv', 'wb')
    period_writer = csv.writer(period_csv)
    period_writer.writerow([
        'run_id', 'region', 'sector', 'subsector', 'technology', 'is_transportation', 'is_agriculture',
        'year', 'share_weight', 'cal_value', 'yield', 'harvests_per_year', 'non_land_variable_cost',
        'fixed_output', 'input_capital', 'input_om_fixed', 'trial_market_price', 'load_factor',
        'ag_prod_change', 'item_name', 'renewable_input'
    ])
    
    energy_demand_csv = open('energy_demand.csv', 'wb')
    energy_demand_writer = csv.writer(energy_demand_csv)
    energy_demand_writer.writerow(['run_id', 'region', 'demand_item', 'value_type', 'year', 'value'])
    
    tech_emission_csv = open('tech_emission.csv', 'wb')
    tech_emission_writer = csv.writer(tech_emission_csv)
    tech_emission_writer.writerow([
        'run_id', 'region', 'sector', 'subsector', 'technology', 'year', 'chem', 'emiss_coef']) 

    tag_stack = []
    elem_stack = []
    for event, elem in doc:
        if event == 'start':
            tag_stack.append(elem.tag)
            elem_stack.append(elem)
            
            if in_database or in_consumer:
                # skip the tech database and consumer elements for now
                continue

            if elem.tag == 'global-technology-database':
                in_database = True
            elif elem.tag == 'gcam-consumer':
                in_consumer = True

            elif elem.tag == 'region':
                region_name = elem.attrib['name']
                region_elem = elem
                print region_name

            elif elem.tag == 'supplysector':
                sector_name = elem.attrib['name']
                is_ag = False
                is_sector = True
            elif elem.tag == 'AgSupplySector':
                sector_name = elem.attrib['name']
                is_ag = True
                is_sector = True
            elif elem.tag == 'depresource':
                resource_name = elem.attrib['name']
                is_resource = True
            elif elem.tag == 'renewresource':
                resource_name = elem.attrib['name']
                is_resource = True
            elif elem.tag == 'unlimited-resource':
                resource_name = elem.attrib['name']
                is_resource = True
            elif elem.tag == 'energy-final-demand':
                demand_name = elem.attrib['name']
                is_final_demand = True

            elif elem.tag == 'subsector':
                subsector_name = elem.attrib['name']
                is_transportation = False
                is_ag = False
            elif elem.tag == 'tranSubsector':
                subsector_name = elem.attrib['name']
                is_transportation = True
                is_ag = False
            elif elem.tag == 'AgSupplySubsector':
                subsector_name = elem.attrib['name']
                is_transportation = False
                is_ag = True

            elif elem.tag == 'technology':
                technology_name = elem.attrib['name']
                is_stub = False
            elif elem.tag == 'stub-technology':
                technology_name = elem.attrib['name']
                is_stub = True
            elif elem.tag == 'AgProductionTechnology':
                technology_name = elem.attrib['name']
                is_stub = False
            elif elem.tag == 'UnmanagedLandTechnology':
                technology_name = elem.attrib['name']
                is_stub = False

            elif elem.tag == 'price':
                year = elem.attrib['year']
                value = elem.text
                if is_sector:
                    price_writer.writerow([run_id, region_name, sector_name, 'sector', year, value])
                elif is_resource:
                    price_writer.writerow([run_id, region_name, resource_name, 'resource', year, value])
                else:
                    print 'price found in price {}/{}'.format(sector_name, subsector_name)
                    # print_location(elem_stack)
                    # sys.exit(0)

            elif elem.tag == 'share-weight':
                if technology_name == '':
                    # a subsector weight
                    year = elem.attrib['year']
                    value = elem.text
                    subsector_shareweight_writer.writerow(
                        [run_id, region_name, sector_name, subsector_name, is_transportation, is_ag, year, value])
                else:
                    # a technology weight
                    pass

            elif elem.tag == 'period':
                period_obj = XmlDictConfig(elem)
                # exempt = set(['minicam-energy-input', 'CalDataOutput', 'CO2', 'Non-CO2', 'share-weight', 
                #     'minicam-non-energy-input', 'fixedOutput', 'fractional-secondary-output', 
                #     'input-capital', 'input-OM-fixed', 'yield', 'nonLandVariableCost', 'harvests-per-year', 
                #     'internal-gains', 'trial-market-price', 'loadFactor', 'residue-biomass-production',
                #     'agProdChange', 'renewable-input', 'itemName'])
                # x = [(k, len(v)) for k, v in period_obj.items() if not k.startswith('__') and not k in exempt]
                # if len(x) > 0:
                #     print x
                year = period_obj['__attrib']['year']
                period_year = year

                # minicam-energy-input and Non-CO2 are the two variable-length ones

                # Ignoring for now
                # - internal-gains
                # - CO2
                # - fractional-secondary-output
                # - residue-biomass-production
                # - minicam-non-energy-input

                row = [
                    run_id,
                    region_name,
                    sector_name,
                    subsector_name,
                    technology_name,
                    is_transportation,
                    is_ag,
                    year,
                    get_float_from_child(period_obj, 'share-weight'),
                    get_float_from_grandchild(period_obj, 'CalDataOutput', 'calOutputValue'),
                    get_float_from_child(period_obj, 'yield'),
                    get_float_from_child(period_obj, 'harvests-per-year'),
                    get_float_from_child(period_obj, 'nonLandVariableCost'),
                    get_float_from_child(period_obj, 'fixedOutput'),
                    get_float_from_grandchild(period_obj, 'input-capital', 'capacity-factor'),
                    get_float_from_grandchild(period_obj, 'input-OM-fixed', 'capacity-factor'),
                    get_float_from_child(period_obj, 'trial-market-price'),
                    get_float_from_child(period_obj, 'loadFactor'),
                    get_float_from_child(period_obj, 'agProdChange'),
                    get_text_from_child(period_obj, 'itemName'),
                    'renewable_input' in period_obj
                ]
                period_writer.writerow(row)

            elif elem.tag == 'Non-CO2':
                if is_resource:
                    pass
                elif is_sector:
                    obj = XmlDictConfig(elem)

                    tech_emission_writer.writerow([
                        run_id, region_name, sector_name, subsector_name, 
                        technology_name, period_year, elem.attrib['name'], 
                        get_float_from_child(obj, 'emiss-coef')])

            elif elem.tag in ['base-service', 'price-elasticity', 'income-elasticity']:
                year = elem.attrib['year']
                try:
                    value = float(elem.text)
                    energy_demand_writer.writerow([run_id, region_name, demand_name, elem.tag, year, value])
                except TypeError:
                    pass

        elif event == 'end':
            try:
                if elem.tag == 'global-technology-database':
                    in_database = False
                elif elem.tag == 'gcam-consumer':
                    in_consumer = False
                elif elem.tag == 'region':
                    # sys.exit(0)
                    region_name = ''
                    # need the following to clear the memory from the previous region
                    region_elem.clear()
                elif elem.tag == 'supplysector':
                    sector_name = ''
                    is_sector = False
                elif elem.tag == 'AgSupplySector':
                    sector_name = ''
                    is_sector = False
                    is_ag = False
                elif elem.tag == 'subsector':
                    subsector_name = ''
                elif elem.tag == 'tranSubsector':
                    subsector_name = ''
                    is_transportation = False
                elif elem.tag == 'AgSupplySubsector':
                    subsector_name = ''
                elif elem.tag in ['technology', 'stub-technology', 'AgProductionTechnology', 'UnmanagedLandTechnology']:
                    technology_name = ''
                    is_stub = False
                elif elem.tag in ['depresource', 'renewresource', 'unlimited-resource']:
                    resource_name = ''
                    is_resource = False
                elif elem.tag == 'energy-final-demand':
                    demand_name = ''
                    is_final_demand = False
                elif elem.tag == 'period':
                    period_year = ''
                tag_stack.pop()
                elem_stack.pop()
            except IndexError as e:
                # print(e)
                pass

def get_float_from_child(period_obj, tag):
    ret = ''
    el = period_obj.get(tag, [None])[0]
    if el is not None:
        try:
            ret = float(el['__text'])
        except TypeError, e:
            # print e
            pass
    return ret


def get_text_from_child(period_obj, tag):
    ret = ''
    el = period_obj.get(tag, [None])[0]
    if el is not None:
        ret = el['__text']
    return ret


def get_float_from_grandchild(period_obj, tag, ctag):
    ret = ''
    el = period_obj.get(tag, [None])[0]
    if el is not None:
        c_el = el.get(ctag, [None])[0]
        if c_el is not None:
            try:
                ret = float(c_el['__text'])
            except TypeError, e:
                pass
                # print e
    return ret


def print_location(elem_stack):
    x = ["[{} {}]".format(e.tag, e.attrib.get('name', '')) for e in elem_stack]
    print x

if __name__ == '__main__':
    filename = sys.argv[1]
    print('Parsing {}'.format(filename))
    parse(filename, 'abcdef')
