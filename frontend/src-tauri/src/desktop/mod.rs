pub mod service;

#[cfg(target_os = "windows")]
pub mod windows;

#[cfg(not(target_os = "windows"))]
pub mod mock;

pub mod permissions;
pub mod dispatcher;
