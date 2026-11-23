{
  description = "lastbook-kit: get, check and serve Lastbook libraries without the desktop app";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    # upstream/ is a git submodule. The package needs it in the source.
    self.submodules = true;
  };

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" ];
      forAll = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});

      # Python libzim isn't in nixpkgs. Wrap the published manylinux wheel, which bundles libzim itself.
      libzimWheels = {
        x86_64-linux = {
          url = "https://files.pythonhosted.org/packages/90/f3/3a437fe17dcf4296400ae50c7cb2b3f0aa20347cdc8c3af1c091d4bdc027/libzim-3.13.1-cp313-cp313-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl";
          sha256 = "03a9ab549d0f14169a64991cab3d26e8923d215af36ae75cc18fb0ae914fa5c0";
        };
        aarch64-linux = {
          url = "https://files.pythonhosted.org/packages/5b/5e/1f0b6d6d5d07b35235420343f7a75fa318a00e7d57bd58e32ea7d10053fc/libzim-3.13.1-cp313-cp313-manylinux_2_27_aarch64.manylinux_2_28_aarch64.whl";
          sha256 = "49d671567d9b0526d62ecccad087f7787379faa9ec823e72e58d7dea5d3f9e6d";
        };
      };

      pythonFor = pkgs: pkgs.python313;

      libzimFor = pkgs:
        let py = pythonFor pkgs; in
        py.pkgs.buildPythonPackage {
          pname = "libzim";
          version = "3.13.1";
          format = "wheel";
          src = pkgs.fetchurl libzimWheels.${pkgs.stdenv.hostPlatform.system};
          nativeBuildInputs = [ pkgs.autoPatchelfHook ];
          buildInputs = [ pkgs.stdenv.cc.cc.lib pkgs.zlib ];
          pythonImportsCheck = [ "libzim" ];
        };

      # Libraries the PyPI wheels expect from the system, for `uv sync` in the dev shell on NixOS.
      wheelLibs = pkgs: [ pkgs.stdenv.cc.cc.lib pkgs.zlib ];
    in
    {
      packages = forAll (pkgs:
        let py = pythonFor pkgs; in
        rec {
          lbx = py.pkgs.buildPythonApplication {
            pname = "lastbook-kit";
            version = (builtins.fromTOML (builtins.readFile ./pyproject.toml)).project.version;
            pyproject = true;
            src = ./.;
            build-system = [ py.pkgs.hatchling ];
            dependencies = [
              (libzimFor pkgs)
              py.pkgs.numpy
              py.pkgs.beautifulsoup4
              py.pkgs.pypdfium2
            ];
            # Upstream's program files, read only. Data folders are always outside the store.
            makeWrapperArgs = [ "--set-default" "LBX_UPSTREAM" "${./upstream}" ];
            nativeCheckInputs = [ py.pkgs.pytestCheckHook ];
            preCheck = "export LBX_UPSTREAM=${./upstream}";
            pythonImportsCheck = [ "lbx" ];
            meta = {
              description = "Get, check and serve Lastbook libraries without the desktop app";
              license = pkgs.lib.licenses.mit;
              mainProgram = "lbx";
            };
          };
          default = lbx;
        });

      devShells = forAll (pkgs: {
        default = pkgs.mkShell {
          packages = [ (pythonFor pkgs) pkgs.uv pkgs.just ];
          env = {
            UV_PYTHON = "${pythonFor pkgs}/bin/python3";
            UV_PYTHON_DOWNLOADS = "never";
            LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath (wheelLibs pkgs);
          };
        };
      });
    };
}
