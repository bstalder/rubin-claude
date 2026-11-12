#!/usr/bin/env bash
# Create a Jupyter kernel on SDF that runs EUPS setup before starting python,
# so `import lsst.daf.butler`, `lsst.sphgeom` and `lsst.summit.utils` work.
#
#   make_sdf_kernel.sh                       # uses the env loadLSST.bash defaults to
#   make_sdf_kernel.sh lsst-scipipe-14.0.0   # pin a specific conda env
#   EXTRA_SETUP="summit_utils" make_sdf_kernel.sh   # extra EUPS products (default: summit_utils)
#
# Not needed on the RSP, where the LSST kernel is already set up.
set -euo pipefail
LOADER=/sdf/group/rubin/sw/loadLSST.bash
ENV_NAME=${1:-}
EXTRA_SETUP=${EXTRA_SETUP-summit_utils}
if [ -z "$ENV_NAME" ]; then
  ENV_NAME=$(bash -c "source $LOADER >/dev/null 2>&1; echo \${CONDA_DEFAULT_ENV:-}")
fi
[ -n "$ENV_NAME" ] || { echo "could not determine conda env; pass it explicitly" >&2; exit 1; }

LAUNCH_DIR=$HOME/.local/kernel-launchers
KDIR=$HOME/.local/share/jupyter/kernels/$ENV_NAME
mkdir -p "$LAUNCH_DIR" "$KDIR"
LAUNCHER=$LAUNCH_DIR/$ENV_NAME.sh

cat > "$LAUNCHER" <<EOF
#!/usr/bin/env bash
export LSST_CONDA_ENV_NAME=$ENV_NAME
source $LOADER
setup lsst_distrib
for p in $EXTRA_SETUP; do setup "\$p" || echo "warning: setup \$p failed" >&2; done
exec python -m ipykernel_launcher "\$@"
EOF
chmod +x "$LAUNCHER"

cat > "$KDIR/kernel.json" <<EOF
{
  "argv": ["$LAUNCHER", "-f", "{connection_file}"],
  "display_name": "LSST ${ENV_NAME#lsst-scipipe-} (lsst_distrib${EXTRA_SETUP:+ + $EXTRA_SETUP})",
  "language": "python"
}
EOF
echo "kernel '$ENV_NAME' -> $KDIR (launcher $LAUNCHER)"
echo "use with: run_cells.py NB --kernel $ENV_NAME"
