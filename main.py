import hazardous
import subprocess
import os
import argparse
import shlex


def main(args):
    file_path = args.source_file
    only_asm = args.asm

    scanner = hazardous.Scanner()
    preprocessor = hazardous.Preprocessor()
    parser = hazardous.Parser()
    generator = hazardous.Generator()

    f = open(file_path, "r")
    code = f.read()
    f.close()

    fn_no_ext = os.path.splitext(file_path)[0]
    program_dir = os.path.dirname(fn_no_ext)

    scanner.input(code, file_path)
    preprocessed = preprocessor.preprocess(list(scanner.tokens()), ['./', './include/', program_dir + "/"])
    tree = parser.parse(preprocessed)
    asm = generator.generate(tree)

    asm_path = fn_no_ext + ".asm"

    with open(asm_path, "w") as f:
        f.write(asm)

    print(f"[INFO] Generated assembly file: {asm_path}")
    if only_asm:
        exit(0)
    
    nasm_exit = subprocess_call_info(["fasm", "-m", "524288", asm_path])
    if nasm_exit != 0:
        print(f"FASM exited with code {nasm_exit}\n")
        exit(1)

    compile_windows(args, fn_no_ext)

    if args.clean:
        os.remove(asm_path)
        os.remove(fn_no_ext + ".obj")


def compile_windows(args, file_name):
    gcc_exit = subprocess_call_info(["gcc", "-m64", "-g", file_name + ".obj", "-o", file_name + ".exe"])

    if gcc_exit != 0:
        print(f"GCC exited with code {gcc_exit}\n")
        exit(1)

    
    if args.run:
        subprocess_call_info([f".\{file_name}.exe"])



def subprocess_call_info(cmd, silent: bool=False) -> int:
    if not silent:
        print("[CMD] %s" % " ".join(map(shlex.quote, cmd)))
    return subprocess.call(cmd)


def handle_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('source_file', type=str)
    parser.add_argument('--asm', action='store_true', help='Only generates the assembly file')
    parser.add_argument('--run', action='store_true', help='Run the program after compiling (if successful)')
    parser.add_argument('--clean', action='store_true', help='Cleans the ASM and OBJ file')
    args = parser.parse_args()

    try:
        main(args)
    except (hazardous.ParserError, hazardous.ScannerError, hazardous.GeneratorError, hazardous.PreprocessorError) as e:
        print(e)
        exit(1)


if __name__ == "__main__":
    handle_args()