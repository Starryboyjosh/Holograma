#!/bin/sh
export LD_LIBRARY_PATH="/home/escoto/Documentos/Holograma/piper/piper"
exec /usr/local/bin/piper --espeak_data /home/escoto/Documentos/Holograma/piper/piper/espeak-ng-data "$@"
