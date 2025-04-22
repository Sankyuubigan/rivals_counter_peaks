{
  pkgs ? import <nixpkgs> {},
}:
let
  python = pkgs.python312;
in
  pkgs.mkShell {
    buildInputs = [ 
      python
      python.pkgs.opencv4
      python.pkgs.pandas
      python.pkgs.ipykernel
    ];
    shellHook = ''export PYTHONPATH=.'';
}