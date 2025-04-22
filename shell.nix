{
  pkgs ? import <nixpkgs> {},
}:
pkgs.mkShell {
    buildInputs = [
      pkgs.python311
      pkgs.python311Packages.opencv4
      pkgs.python311Packages.pip
      pkgs.python311Packages.ipykernel
      pkgs.python311Packages.pandas
    ];
  }