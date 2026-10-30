import json
import subprocess
import os

def build_single_line_measures():
    from pathlib import Path
    source = Path(__file__).resolve().parents[1] / 'powerbi/CHHHS Research Publications.SemanticModel/definition/tables/Publication.tmdl'
    with source.open() as f:
        lines = f.read().splitlines()

    measure_blocks = []
    current = []
    in_m = False
    for line in lines:
        s = line.strip()
        if s.startswith('measure '):
            if current:
                measure_blocks.append(current)
                current = []
            in_m = True
        elif s.startswith('partition ') or s.startswith('table ') or s.startswith('column '):
            if current:
                measure_blocks.append(current)
                current = []
            in_m = False
        
        if in_m:
            current.append(line)

    if current:
        measure_blocks.append(current)

    print(f"Parsed {len(measure_blocks)} measures")

    formatted_measures = []
    for b in measure_blocks:
        header = b[0].strip()
        parts = header.split('=', 1)
        m_decl = parts[0].strip()
        first_dax = parts[1].strip() if len(parts) > 1 else ''
        
        dax_tokens = []
        if first_dax:
            dax_tokens.append(first_dax)
            
        props = []
        for l in b[1:]:
            s = l.strip()
            if s.startswith('formatString:') or s.startswith('lineageTag:'):
                props.append(s)
            elif s:
                dax_tokens.append(s)

        single_line_dax = ' '.join(dax_tokens)
        m_tmdl = f"\t\t{m_decl} = {single_line_dax}"
        for p in props:
            m_tmdl += f"\n\t\t\t{p}"
        formatted_measures.append(m_tmdl)

    tmdl = "createOrReplace\n\n\tref table Publication\n\n" + "\n\n".join(formatted_measures)
    return tmdl

def main():
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser(description='Prepare measure text locally; native UI automation is retired.')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = Path(args.output).resolve()
    if not output.is_relative_to(root / 'private' / 'ops'):
        raise ValueError('Output must remain private/ops')
    subprocess.run(['git', 'check-ignore', '-q', str(output)], cwd=root, check=True)
    with os.fdopen(os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as handle:
        handle.write(build_single_line_measures())
    print('PASS_LOCAL_ONLY: measure text prepared; use the complete definition packet route')

if __name__ == '__main__': main()
