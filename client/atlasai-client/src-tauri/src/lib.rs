use std::sync::Mutex;
use tauri::Manager;
use tauri_plugin_shell::{process::CommandChild, ShellExt};

struct BackendState(Mutex<Option<CommandChild>>);

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let (_rx, child) = app
                .shell()
                .sidecar("atlasai-backend")
                .expect("failed to prepare atlasai-backend sidecar")
                .spawn()
                .expect("failed to start atlasai-backend sidecar");

            app.manage(BackendState(Mutex::new(Some(child))));
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}