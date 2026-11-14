import curses
import os
import time
from client.ftp_client import FTPClient

class DualPaneTUI:
    def __init__(self, ftp_client):
        self.client = ftp_client
        self.local_dir = os.path.realpath("storage/client_workspace")
        os.makedirs(self.local_dir, exist_ok=True)
        
        self.local_files = []
        self.remote_files = []
        
        self.active_pane = 0 # 0 = Left (Local), 1 = Right (Remote)
        self.local_idx = 0
        self.remote_idx = 0
        
        self.status_msg = "Ready. Press 'c' to connect, 'q' to quit."

    def refresh_local(self):
        try:
            self.local_files = [".."] + os.listdir(self.local_dir)
        except Exception:
            self.local_files = ["Error reading local directory"]

    def refresh_remote(self):
        if self.client.is_connected:
            try:
                # Assuming the client's list() method returns a newline-separated string
                listing = self.client.list()
                # Parse the raw LIST output into simple filenames for the UI
                self.remote_files = [".."] + [line.split()[-1] for line in listing.split('\n') if line.strip()]
            except Exception as e:
                self.remote_files = [f"Error: {e}"]
        else:
            self.remote_files = ["Not connected."]

    def draw(self, stdscr):
        # 1. Safely hide cursor (prevents silent crashes on some terminals)
        try:
            curses.curs_set(0) 
        except curses.error:
            pass
            
        # 2. THE FIX: Initialize and refresh the main background screen FIRST!
        stdscr.clear()
        stdscr.refresh()
        
        self.refresh_local()
        self.refresh_remote()

        # Create Windows
        height, width = stdscr.getmaxyx()
        left_width = width // 2
        right_width = width - left_width
        
        left_win = curses.newwin(height - 3, left_width, 0, 0)
        right_win = curses.newwin(height - 3, right_width, 0, left_width)
        status_win = curses.newwin(3, width, height - 3, 0)

        while True:
            # Erase the individual windows
            left_win.erase()
            right_win.erase()
            status_win.erase()
            
            left_win.box()
            right_win.box()
            status_win.box()
            
            # Draw Titles 
            left_win.addstr(0, 2, f" LOCAL: {os.path.basename(self.local_dir)} ", curses.A_BOLD)
            
            remote_title = "Disconnected"
            if self.client.is_connected:
                try:
                    remote_title = self.client.pwd()
                except Exception:
                    remote_title = "Not Authenticated"
            right_win.addstr(0, 2, f" REMOTE: {remote_title} ", curses.A_BOLD)
            
            # Draw Local Files
            for i, file in enumerate(self.local_files[:height-5]):
                if self.active_pane == 0 and i == self.local_idx:
                    left_win.addstr(i + 2, 2, file[:left_width-4], curses.A_REVERSE)
                else:
                    left_win.addstr(i + 2, 2, file[:left_width-4])
                    
            # Draw Remote Files
            for i, file in enumerate(self.remote_files[:height-5]):
                if self.active_pane == 1 and i == self.remote_idx:
                    right_win.addstr(i + 2, 2, file[:right_width-4], curses.A_REVERSE)
                else:
                    right_win.addstr(i + 2, 2, file[:right_width-4])
                    
            # Draw Status
            status_win.addstr(1, 2, self.status_msg[:width-4])
            
            # Refresh to screen
            left_win.refresh()
            right_win.refresh()
            status_win.refresh()
            
            # Wait for user input (Blocks until a key is pressed)
            key = stdscr.getch()
            
            if key == ord('q'):
                break
            elif key == 9: # TAB key
                self.active_pane = 1 - self.active_pane
            elif key == curses.KEY_UP:
                if self.active_pane == 0 and self.local_idx > 0:
                    self.local_idx -= 1
                elif self.active_pane == 1 and self.remote_idx > 0:
                    self.remote_idx -= 1
            elif key == curses.KEY_DOWN:
                if self.active_pane == 0 and self.local_idx < len(self.local_files) - 1:
                    self.local_idx += 1
                elif self.active_pane == 1 and self.remote_idx < len(self.remote_files) - 1:
                    self.remote_idx += 1
            elif key == ord('c'):
                self.status_msg = "Connecting to 127.0.0.1:2121..."
                try:
                    self.client.connect("127.0.0.1", 2121)
                    self.client.login("admin", "password123")
                    self.refresh_remote()
                    self.status_msg = "Connected! [TAB] Switch Pane | [UP/DOWN] Navigate | [Q]uit"
                except Exception as e:
                    self.status_msg = f"Connection failed: {e}"

class SilentLogger:
    """A dummy logger that intercepts and mutes all background prints to prevent screen corruption."""
    def __getattr__(self, name):
        return lambda *args, **kwargs: None

def start_tui():
    client = FTPClient(show_wire=False)
    client.logger = SilentLogger()  # Mute the background prints!
    tui = DualPaneTUI(client)
    curses.wrapper(tui.draw)

if __name__ == "__main__":
    start_tui()