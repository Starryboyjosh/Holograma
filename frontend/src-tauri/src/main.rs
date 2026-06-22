// Evita abrir una consola adicional en Windows en builds release.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    holograma_lib::run();
}
