{
    inputs = {
        nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
        flake-utils.url = "github:numtide/flake-utils";
    };
    outputs = {self, nixpkgs, flake-utils}:
        flake-utils.lib.eachDefaultSystem (system:
            let
                pkgs = nixpkgs.legacyPackages.${system};
            in
            with pkgs;
            {
                devShells.default = mkShell {
                    buildInputs = [
                        python312
                        python312Packages.pip
                        python312Packages.virtualenv
                        uv
                        protobuf
                    ];
                    # Make libraries available
                    LD_LIBRARY_PATH = "${stdenv.cc.cc.lib}/lib";

                    shellHook = ''
                      export LD_LIBRARY_PATH=${stdenv.cc.cc.lib}/lib:$LD_LIBRARY_PATH
                    '';
                };
            }
        );
}
