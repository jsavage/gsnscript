import argparse
import os
import sys
import yaml
from collections import defaultdict, OrderedDict

class Diagnostics:
    def __init__(self):
        self.warnings = 0
        self.errors = 0
        self.messages = []

    def add_error(self, module, message):
        self.errors += 1
        self.messages.append(f"Error in {module}: {message}")

    def add_warning(self, module, message):
        self.warnings += 1
        self.messages.append(f"Warning in {module}: {message}")

def read_inputs(inputs, nodes, modules, diags):
    for input_file in inputs:
        try:
            with open(input_file, 'r') as f:
                data = yaml.safe_load(f)
        except Exception as e:
            diags.add_error(None, f"Failed to open or parse file {input_file}: {str(e)}")
            continue

        module_name = data.get("module", os.path.splitext(os.path.basename(input_file))[0])
        if module_name in modules:
            diags.add_error(module_name, f"Module name {module_name} in {input_file} already present.")
            continue

        modules[module_name] = {'filename': input_file, 'meta': data.get("meta", {})}
        
        for node_name, node_data in data.items():
            if node_name in nodes:
                diags.add_error(module_name, f"Element {node_name} in {input_file} already present.")
                continue
            nodes[node_name] = node_data
            nodes[node_name]['module'] = module_name

    if not nodes:
        raise ValueError("No input elements found.")

def validate_and_check(nodes, modules, diags, excluded_modules, layers):
    for module_name, module_info in modules.items():
        validate_module(diags, module_name, module_info, nodes)
        if diags.errors > 0:
            return
    extend_modules(diags, nodes, modules)
    check_nodes(diags, nodes, excluded_modules)
    if layers:
        check_layers(diags, nodes, layers)

def print_outputs(nodes, modules, render_options):
    if not render_options['skip_argument']:
        for module_name, module in modules.items():
            output_filename = os.path.splitext(module['filename'])[0] + '.svg'
            render_argument(output_filename, module_name, modules, nodes, render_options)
    
    if len(modules) > 1:
        if not render_options['skip_architecture']:
            output_filename = 'architecture.svg'
            render_architecture(output_filename, modules, nodes, render_options)
        
        if not render_options['skip_complete']:
            output_filename = 'complete.svg'
            render_complete(output_filename, nodes, render_options)

    if not render_options['skip_evidences']:
        output_filename = 'evidences.md'
        render_evidences(output_filename, nodes, render_options)

def output_messages(diags):
    for msg in diags.messages:
        print(msg, file=sys.stderr)

    if diags.errors == 0:
        if diags.warnings > 0:
            print(f"Warning: {diags.warnings} warnings detected.", file=sys.stderr)
    else:
        raise Exception(f"{diags.errors} errors and {diags.warnings} warnings detected.")

def main():
    parser = argparse.ArgumentParser(description="Process GSN YAML files.")
    parser.add_argument("INPUT", nargs='+', help="Sets the input file(s) to use.")
    parser.add_argument("-c", "--check", action="store_true", help="Only check the input file(s), but do not output graphs.")
    parser.add_argument("-x", "--exclude", action="append", help="Exclude this module from reference checks.")
    parser.add_argument("-N", "--no-arg", action="store_true", help="Do not output argument view.")
    parser.add_argument("-f", "--full", help="Output the complete view to <COMPLETE_VIEW>.")
    parser.add_argument("-F", "--no-full", action="store_true", help="Do not output the complete view.")
    parser.add_argument("-a", "--arch", help="Output the architecture view to <ARCHITECTURE_VIEW>.")
    parser.add_argument("-A", "--no-arch", action="store_true", help="Do not output the architecture view.")
    parser.add_argument("-e", "--evidences", action="append", help="Output list of all evidences to <EVIDENCES>.")
    parser.add_argument("-E", "--no-evidences", action="store_true", help="Do not output list of all evidences.")
    parser.add_argument("-l", "--layer", action="append", help="Output additional layer. Can be used multiple times.")
    parser.add_argument("-s", "--stylesheet", action="append", help="Links a stylesheet in SVG output.")
    parser.add_argument("-t", "--embed-css", action="store_true", help="Embed stylesheets instead of linking them.")
    parser.add_argument("-G", "--no-legend", action="store_true", help="Do not output a legend based on module information.")
    parser.add_argument("-g", "--full-legend", action="store_true", help="Output a legend based on all module information.")

    args = parser.parse_args()

    inputs = args.INPUT
    layers = args.layer or []
    excluded_modules = args.exclude or []
    
    diags = Diagnostics()
    nodes = OrderedDict()
    modules = {}

    try:
        read_inputs(inputs, nodes, modules, diags)
        validate_and_check(nodes, modules, diags, excluded_modules, layers)
        if diags.errors == 0 and not args.check:
            render_options = {
                'skip_argument': args.no_arg,
                'skip_complete': args.no_full,
                'skip_architecture': args.no_arch,
                'skip_evidences': args.no_evidences,
                'complete_filename': args.full,
                'architecture_filename': args.arch,
                'evidences_filename': args.evidences,
                'embed_css': args.embed_css
            }
            print_outputs(nodes, modules, render_options)
    except Exception as e:
        diags.add_error(None, str(e))

    output_messages(diags)

if __name__ == "__main__":
    main()
