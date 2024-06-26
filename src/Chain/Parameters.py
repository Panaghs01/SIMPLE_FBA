import yaml


def read_yaml(path):
    with open(path, 'rb') as f:
        data = yaml.safe_load(f)
    return data


class Parameters:
    '''
        Contains all the parameters defining the simulator
    '''
    simulation = {}
    application = {}
    execution = {}
    data = {}
    consensus = {}
    network = {}

    BigFoot = {}
    PBFT = {}
    FBA = {}
    
    CPs = {}

    tx_factory = None

    @staticmethod
    def reset_params():
        Parameters.simulation = {}
        Parameters.application = {}
        Parameters.execution = {}
        Parameters.data = {}
        Parameters.consensus = {}
        Parameters.network = {}
        Parameters.BigFoot = {}
        Parameters.PBFT = {}
        Parameters.FBA = {}
        Parameters.CPs = {}
        Parameters.tx_factory = None

    @staticmethod
    def load_params_from_config(config):
        params = read_yaml(f"Configs/{config}")

        try:
            Parameters.simulation = params["simulation"]
        except KeyError:
            print("NO 'simulation' Parameters")

        Parameters.simulation["events"] = {}  # cnt events of each type
        Parameters.simulation['event_id'] = 0 # used to assing events incremental IDs

        try:
            Parameters.network = params["network"]
        except KeyError:
            print("NO 'network' Parameters")

        try:
            Parameters.application = params["application"]
            Parameters.calculate_fault_tolerance()
        except KeyError:
            print("NO 'application' Parameters")

        Parameters.application["txIDS"] = 0

        try:
            Parameters.execution = params["execution"]
        except KeyError:
            print("NO 'execution' Parameters")

        try:
            Parameters.data = params["data"]
        except KeyError:
            print("NO 'data' Parameters")
            
        Parameters.BigFoot = read_yaml(params['consensus']['BigFoot'])
        Parameters.PBFT = read_yaml(params['consensus']['PBFT'])
        Parameters.FBA = read_yaml(params['consensus']['FBA'])

    @staticmethod
    def calculate_fault_tolerance():
        Parameters.application["f"] = int((1/3) * Parameters.application["Nn"])

        Parameters.application["required_messages"] = (
            2 * Parameters.application["f"]) + 1

    @staticmethod
    def parameters_to_string():
        p_name_size = 30
        s = ''

        def dict_to_str(x):
            return '\n'.join([f'{f"%{p_name_size}s"%key}: {value}' for key, value in x.items()])

        s += '-'*20 + "SIMULATION" + "-"*20 + '\n'
        s += dict_to_str(Parameters.simulation) + '\n'

        s += '-'*20 + "APPLICATION" + "-"*20 + '\n'
        s += dict_to_str(Parameters.application) + '\n'

        s += '-'*20 + "EXECUTION" + "-"*20 + '\n'
        s += dict_to_str(Parameters.execution) + '\n'

        s += '-'*20 + "DATA" + "-"*20 + '\n'
        s += dict_to_str(Parameters.data) + '\n'

        s += '-'*20 + "NETWORK" + "-"*20 + '\n'
        s += dict_to_str(Parameters.network) + '\n'

        return s
