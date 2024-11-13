import streamlit as st
import requests
import os
import hashlib
from pathlib import Path
import platform
import psutil
from tqdm import tqdm
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
from datetime import datetime, timedelta
import threading
import time

class LinkManager:
    def __init__(self):
        self.cache_file = "os_links_cache.json"
        self.cache_duration = timedelta(hours=24)
        self.lock = threading.Lock()
        
    def load_cache(self):
        try:
            with open(self.cache_file, 'r') as f:
                cache = json.load(f)
                if datetime.fromisoformat(cache['timestamp']) + self.cache_duration > datetime.now():
                    return cache['links']
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            pass
        return None

    def save_cache(self, links):
        cache = {
            'timestamp': datetime.now().isoformat(),
            'links': links
        }
        with open(self.cache_file, 'w') as f:
            json.dump(cache, f)

    def get_ubuntu_link(self, version):
        try:
            response = requests.get(f"https://releases.ubuntu.com/{version}/")
            soup = BeautifulSoup(response.text, 'html.parser')
            for link in soup.find_all('a'):
                href = link.get('href', '')
                if 'desktop-amd64.iso' in href:
                    return urljoin(f"https://releases.ubuntu.com/{version}/", href)
        except Exception:
            return None

    def get_fedora_link(self, version):
        base_url = f"https://download.fedoraproject.org/pub/fedora/linux/releases/{version}/Workstation/x86_64/iso/"
        try:
            response = requests.get(base_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            for link in soup.find_all('a'):
                href = link.get('href', '')
                if re.search(r'Fedora-Workstation-Live-x86_64-.*\.iso$', href):
                    return urljoin(base_url, href)
        except Exception:
            return None

    def get_debian_link(self, version_type="NET"):
        try:
            if version_type == "NET":
                response = requests.get("https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/")
            else:
                response = requests.get("https://cdimage.debian.org/debian-cd/current/amd64/iso-dvd/")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            for link in soup.find_all('a'):
                href = link.get('href', '')
                if 'netinst.iso' in href or 'DVD-1.iso' in href:
                    return urljoin(response.url, href)
        except Exception:
            return None

    def get_mint_link(self, version, edition):
        try:
            base_url = f"https://mirrors.edge.kernel.org/linuxmint/stable/{version}/"
            response = requests.get(base_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            for link in soup.find_all('a'):
                href = link.get('href', '')
                if f'linuxmint-{version}-{edition}-64bit.iso' in href.lower():
                    return urljoin(base_url, href)
        except Exception:
            return None

    def get_elementary_link(self):
        try:
            # elementary OS uses a CDN system, we'll use their direct download link
            version = "7.1"  # Current stable version
            timestamp = "20231031"  # Release timestamp
            base_url = "https://objects.githubusercontent.com/github-production-release-asset-2e65be"
            
            # This is their current direct download link pattern
            direct_url = f"{base_url}/elementary-os-{version}-stable.{timestamp}.iso"
            
            # Verify if the URL exists
            response = requests.head(direct_url)
            if response.status_code == 200:
                return direct_url
            
            # Fallback to alternate CDN
            fallback_url = f"https://sgp1.dl.elementary.io/elementary-os-{version}-stable.{timestamp}.iso"
            response = requests.head(fallback_url)
            if response.status_code == 200:
                return fallback_url
            
            # Second fallback to their download page
            return "https://elementary.io/download"
        except Exception as e:
            st.error(f"Error getting elementary OS link: {str(e)}")
            return None

    def get_popos_link(self, version, nvidia=False):
        try:
            # First, get the latest build number
            base_url = "https://iso.pop-os.org"
            path = f"/{version}/amd64/{'nvidia' if nvidia else 'intel'}"
            
            response = requests.get(f"{base_url}{path}")
            if response.status_code == 200:
                # Find the latest build number
                soup = BeautifulSoup(response.text, 'html.parser')
                latest_build = None
                for link in soup.find_all('a'):
                    href = link.get('href', '')
                    if href.isdigit():  # Build numbers are digits
                        if not latest_build or int(href) > int(latest_build):
                            latest_build = href
                
                if latest_build:
                    # Construct the final URL with build number
                    gpu_type = 'nvidia' if nvidia else 'intel'
                    filename = f"pop-os_{version}_amd64_{gpu_type}_{latest_build}.iso"
                    final_url = f"{base_url}{path}/{latest_build}/{filename}"
                    
                    # Verify the URL exists
                    response = requests.head(final_url)
                    if response.status_code == 200:
                        return final_url
        except Exception as e:
            st.error(f"Error getting Pop!_OS link: {str(e)}")
            return None

    def get_manjaro_link(self, edition):
        try:
            base_url = "https://download.manjaro.org"
            response = requests.get(f"{base_url}/{edition.lower()}/")
            soup = BeautifulSoup(response.text, 'html.parser')
            latest = None
            for link in soup.find_all('a'):
                href = link.get('href', '')
                if href.endswith('.iso') and 'minimal' not in href.lower():
                    latest = urljoin(base_url, href)
            return latest
        except Exception:
            return None

    def get_kali_link(self, version_type="live"):
        try:
            base_url = "https://cdimage.kali.org/current/"
            response = requests.get(base_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            for link in soup.find_all('a'):
                href = link.get('href', '')
                if version_type == 'live' and 'live-amd64.iso' in href:
                    return urljoin(base_url, href)
                elif version_type == 'installer' and 'installer-amd64.iso' in href:
                    return urljoin(base_url, href)
        except Exception:
            return None

    def get_zorin_link(self, edition):
        try:
            if edition.lower() == 'core':
                return "https://zorinos.com/download/17/core"
            elif edition.lower() == 'lite':
                return "https://zorinos.com/download/17/lite"
        except Exception:
            return None

    def get_arch_link(self):
        try:
            # Primary mirror with known structure
            base_url = "https://archlinux.c3sl.ufpr.br/iso/"
            
            # Get the latest version directory
            response = requests.get(base_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            latest_version = None
            
            # Find the latest version directory
            for link in soup.find_all('a'):
                href = link.get('href', '')
                if re.match(r'\d{4}\.\d{2}\.\d{2}', href):
                    if not latest_version or href > latest_version:
                        latest_version = href
            
            if latest_version:
                # Get the ISO from the latest version directory
                version_url = urljoin(base_url, latest_version)
                response = requests.get(version_url)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Look for the ISO file
                for link in soup.find_all('a'):
                    href = link.get('href', '')
                    if href.endswith('.iso') and 'archlinux-' in href:
                        return urljoin(version_url, href)
            
            # Fallback mirrors if primary fails
            fallback_mirrors = [
                "https://mirror.rackspace.com/archlinux/iso/latest/",
                "https://mirrors.kernel.org/archlinux/iso/latest/"
            ]
            
            for mirror in fallback_mirrors:
                try:
                    response = requests.get(mirror)
                    soup = BeautifulSoup(response.text, 'html.parser')
                    for link in soup.find_all('a'):
                        href = link.get('href', '')
                        if href.startswith('archlinux-') and href.endswith('.iso'):
                            return urljoin(mirror, href)
                except:
                    continue
                
            return None
        except Exception as e:
            st.error(f"Error getting Arch Linux link: {str(e)}")
            return None

    def update_links(self):
        with self.lock:
            cached_links = self.load_cache()
            if cached_links:
                return cached_links

            updated_links = {}
            
            # Ubuntu
            ubuntu_versions = ["24.04", "22.04"]
            for version in ubuntu_versions:
                link = self.get_ubuntu_link(version)
                if link:
                    updated_links[f"ubuntu_{version}"] = link

            # Fedora
            fedora_versions = ["40", "39"]
            for version in fedora_versions:
                link = self.get_fedora_link(version)
                if link:
                    updated_links[f"fedora_{version}"] = link

            # Debian
            debian_links = {
                "debian_net": self.get_debian_link("NET"),
                "debian_dvd": self.get_debian_link("DVD")
            }
            updated_links.update(debian_links)

            # Linux Mint
            mint_editions = ["cinnamon", "mate", "xfce"]
            for edition in mint_editions:
                link = self.get_mint_link("21.3", edition)
                if link:
                    updated_links[f"mint_21.3_{edition}"] = link

            # elementary OS
            elementary_link = self.get_elementary_link()
            if elementary_link:
                updated_links["elementary_os"] = elementary_link

            # Pop!_OS
            popos_versions = ["22.04"]
            for version in popos_versions:
                link = self.get_popos_link(version, nvidia=False)
                if link:
                    updated_links[f"popos_{version}"] = link
                link_nvidia = self.get_popos_link(version, nvidia=True)
                if link_nvidia:
                    updated_links[f"popos_{version}_nvidia"] = link_nvidia

            # Manjaro
            manjaro_editions = ["kde", "gnome", "xfce"]
            for edition in manjaro_editions:
                link = self.get_manjaro_link(edition)
                if link:
                    updated_links[f"manjaro_{edition}"] = link

            # Kali Linux
            kali_types = ["live", "installer"]
            for type_ in kali_types:
                link = self.get_kali_link(type_)
                if link:
                    updated_links[f"kali_{type_}"] = link

            # Zorin OS
            zorin_editions = ["core", "lite"]
            for edition in zorin_editions:
                link = self.get_zorin_link(edition)
                if link:
                    updated_links[f"zorin_{edition}"] = link

            # Arch Linux
            arch_link = self.get_arch_link()
            if arch_link:
                updated_links["arch_latest"] = arch_link

            self.save_cache(updated_links)
            return updated_links

class OSInstaller:
    def __init__(self):
        self.link_manager = LinkManager()
        self.os_data = {
            "Ubuntu": {
                "versions": {
                    "24.04 LTS": {
                        "url": "",
                        "checksum": "sha256:..."
                    },
                    "22.04 LTS": {
                        "url": "",
                        "checksum": "sha256:..."
                    }
                },
                "icon": "🐧"
            },
            "Linux Mint": {
                "versions": {
                    "21.3 Cinnamon": {
                        "url": "https://mirrors.edge.kernel.org/linuxmint/stable/21.3/linuxmint-21.3-cinnamon-64bit.iso",
                        "checksum": "sha256:..."
                    },
                    "21.3 MATE": {
                        "url": "https://mirrors.edge.kernel.org/linuxmint/stable/21.3/linuxmint-21.3-mate-64bit.iso",
                        "checksum": "sha256:..."
                    },
                    "21.3 Xfce": {
                        "url": "https://mirrors.edge.kernel.org/linuxmint/stable/21.3/linuxmint-21.3-xfce-64bit.iso",
                        "checksum": "sha256:..."
                    }
                },
                "icon": "🌿"
            },
            "Pop!_OS": {
                "versions": {
                    "22.04 LTS": {
                        "url": "",
                        "checksum": "sha256:..."
                    },
                    "22.04 LTS NVIDIA": {
                        "url": "",
                        "checksum": "sha256:..."
                    }
                },
                "icon": "💫",
                "note": "Direct download from System76 servers"
            },
            "Fedora": {
                "versions": {
                    "Fedora 40": {
                        "url": "",
                        "checksum": "sha256:..."
                    },
                    "Fedora 39": {
                        "url": "",
                        "checksum": "sha256:..."
                    }
                },
                "icon": "🎩"
            },
            "Debian": {
                "versions": {
                    "12.5.0 NET": {
                        "url": "",
                        "checksum": "sha256:..."
                    },
                    "12.5.0 DVD": {
                        "url": "",
                        "checksum": "sha256:..."
                    }
                },
                "icon": "🔴"
            },
            "Manjaro": {
                "versions": {
                    "KDE": {
                        "url": "",
                        "checksum": "sha256:..."
                    },
                    "GNOME": {
                        "url": "",
                        "checksum": "sha256:..."
                    },
                    "XFCE": {
                        "url": "",
                        "checksum": "sha256:..."
                    }
                },
                "icon": "🎯",
                "note": "Latest stable release will be downloaded"
            },
            "Zorin OS": {
                "versions": {
                    "17 Core": {
                        "url": "https://zorinos.com/download/17/core",
                        "checksum": "sha256:..."
                    },
                    "17 Lite": {
                        "url": "https://zorinos.com/download/17/lite",
                        "checksum": "sha256:..."
                    }
                },
                "icon": "🎨",
                "note": "You'll be redirected to Zorin's download page"
            },
            "elementary OS": {
                "versions": {
                    "7.1 Horus": {
                        "url": "",
                        "checksum": "sha256:..."
                    }
                },
                "icon": "🎯",
                "note": "Direct download from elementary OS servers. If download fails, you'll be redirected to their download page."
            },
            "Kali Linux": {
                "versions": {
                    "Latest Live": {
                        "url": "",
                        "checksum": "sha256:..."
                    },
                    "Latest Installer": {
                        "url": "",
                        "checksum": "sha256:..."
                    }
                },
                "icon": "🐉",
                "note": "Latest version will be downloaded automatically"
            },
            "Windows": {
                "versions": {
                    "Windows 11": {
                        "url": "https://www.microsoft.com/software-download/windows11",
                        "checksum": "sha256:..."
                    },
                    "Windows 10": {
                        "url": "https://www.microsoft.com/software-download/windows10",
                        "checksum": "sha256:..."
                    }
                },
                "icon": "🪟",
                "note": "⚠️ Windows downloads require the Media Creation Tool:\n1. Click Download to visit Microsoft's page\n2. Download and run the Media Creation Tool\n3. Follow the tool's instructions to create installation media"
            },
            "Arch Linux": {
                "versions": {
                    "Latest Release": {
                        "url": "https://archlinux.c3sl.ufpr.br/iso/2024.11.01/archlinux-2024.11.01-x86_64.iso",
                        "checksum": "sha256:..."
                    }
                },
                "icon": "🏹",
                "note": """
                Arch Linux is a lightweight and flexible Linux® distribution that tries to Keep It Simple.
                Note: This is a minimal installation that requires command-line knowledge.
                
                Requirements:
                - 64-bit x86_64 processor
                - Minimum 512 MB RAM (2 GB recommended)
                - Minimum 2 GB disk space (20 GB recommended)
                - Internet connection during installation
                """
            }
        }
        self.update_links()
        self.start_link_updater()
        
    def start_link_updater(self):
        def update_periodically():
            while True:
                self.update_links()
                time.sleep(3600)  # Update every hour
        
        updater_thread = threading.Thread(target=update_periodically, daemon=True)
        updater_thread.start()

    def update_links(self):
        links = self.link_manager.update_links()
        
        # Update the os_data dictionary with new links
        if "ubuntu_24.04" in links:
            self.os_data["Ubuntu"]["versions"]["24.04 LTS"]["url"] = links["ubuntu_24.04"]
        if "ubuntu_22.04" in links:
            self.os_data["Ubuntu"]["versions"]["22.04 LTS"]["url"] = links["ubuntu_22.04"]
        if "fedora_40" in links:
            self.os_data["Fedora"]["versions"]["Fedora 40"]["url"] = links["fedora_40"]
        if "debian_net" in links:
            self.os_data["Debian"]["versions"]["12.5.0 NET"]["url"] = links["debian_net"]
        if "popos_22.04" in links:
            self.os_data["Pop!_OS"]["versions"]["22.04 LTS"]["url"] = links["popos_22.04"]
        if "popos_22.04_nvidia" in links:
            self.os_data["Pop!_OS"]["versions"]["22.04 LTS NVIDIA"]["url"] = links["popos_22.04_nvidia"]
        if "manjaro_kde" in links:
            self.os_data["Manjaro"]["versions"]["KDE"]["url"] = links["manjaro_kde"]
        if "manjaro_gnome" in links:
            self.os_data["Manjaro"]["versions"]["GNOME"]["url"] = links["manjaro_gnome"]
        if "manjaro_xfce" in links:
            self.os_data["Manjaro"]["versions"]["XFCE"]["url"] = links["manjaro_xfce"]
        if "kali_live" in links:
            self.os_data["Kali Linux"]["versions"]["Latest Live"]["url"] = links["kali_live"]
        if "kali_installer" in links:
            self.os_data["Kali Linux"]["versions"]["Latest Installer"]["url"] = links["kali_installer"]
        if "elementary_os" in links:
            self.os_data["elementary OS"]["versions"]["7.1 Horus"]["url"] = links["elementary_os"]
        if "arch_latest" in links:
            self.os_data["Arch Linux"]["versions"]["Latest Release"]["url"] = links["arch_latest"]

    def get_system_info(self):
        """Get current system information"""
        return {
            "os": platform.system(),
            "architecture": platform.machine(),
            "ram": f"{round(psutil.virtual_memory().total / (1024**3))} GB",
            "cpu": platform.processor(),
            "disk_space": f"{round(psutil.disk_usage('/').free / (1024**3))} GB free"
        }

    def download_os(self, url, destination):
        """Download OS with progress bar"""
        try:
            # Handle redirects and get final URL
            session = requests.Session()
            response = session.get(url, stream=True, allow_redirects=True)
            final_url = response.url  # Get the final URL after redirects
            
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            
            if total_size == 0:
                st.error("❌ Couldn't determine file size. Trying alternate method...")
                # Try to get the file size from the server
                response = session.head(final_url)
                total_size = int(response.headers.get('content-length', 0))
                if total_size == 0:
                    st.error("❌ Could not determine file size. Download may not work properly.")
                    return False

            # Continue with the rest of your existing download_os method...
            progress_bar = st.progress(0)
            progress_text = st.empty()
            
            with open(destination, 'wb') as f:
                downloaded = 0
                for data in response.iter_content(chunk_size=1024*1024):
                    downloaded += len(data)
                    f.write(data)
                    progress = int((downloaded / total_size) * 100)
                    progress_bar.progress(progress)
                    progress_text.text(f"Downloaded: {progress}% ({downloaded}/{total_size} bytes)")
            
            return True
        except requests.exceptions.RequestException as e:
            st.error(f"❌ Download failed: {str(e)}")
            return False
        except Exception as e:
            st.error(f"❌ Error during download: {str(e)}")
            return False

    def verify_checksum(self, file_path, expected_checksum):
        """Verify file integrity"""
        # If checksum is not provided or is a placeholder, skip verification
        if not expected_checksum or expected_checksum == "sha256:...":
            st.warning("⚠️ Checksum verification skipped - no checksum provided")
            return True
        
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            calculated_hash = sha256_hash.hexdigest()
            
            # Remove 'sha256:' prefix if present in expected_checksum
            expected_checksum = expected_checksum.replace('sha256:', '')
            
            is_valid = calculated_hash.lower() == expected_checksum.lower()
            if is_valid:
                st.success(f"✅ Checksum verification passed")
            else:
                st.error(f"❌ Checksum mismatch:\nExpected: {expected_checksum}\nGot: {calculated_hash}")
            return is_valid
        except Exception as e:
            st.error(f"Error during checksum verification: {str(e)}")
            return False

    def verify_download_link(self, url):
        """Verify if the download link is working"""
        if not url:
            return False, "No download link available"
        
        try:
            session = requests.Session()
            response = session.head(url, allow_redirects=True)
            
            if response.status_code == 200:
                # Check if it's a direct file download
                content_type = response.headers.get('content-type', '').lower()
                content_length = response.headers.get('content-length')
                
                if 'iso' in content_type or 'octet-stream' in content_type:
                    return True, "Ready for download"
                elif content_length and int(content_length) > 100000000:  # Larger than 100MB
                    return True, "Ready for download"
                elif any(domain in url.lower() for domain in ['microsoft.com', 'zorinos.com', 'elementary.io']):
                    return True, "Redirect to official download page"
                else:
                    return False, "Invalid ISO file"
            else:
                return False, f"Link error: HTTP {response.status_code}"
            
        except requests.exceptions.RequestException as e:
            return False, f"Connection error: {str(e)}"
        except Exception as e:
            return False, f"Verification error: {str(e)}"

def main():
    st.set_page_config(
        page_title="Universal OS Installer",
        page_icon="🖥️",
        layout="wide"
    )

    installer = OSInstaller()
    
    st.title("🖥️ Universal OS Installer")
    st.markdown("### Your one-stop solution for OS installation")

    # System Information
    with st.expander("📊 System Information", expanded=True):
        sys_info = installer.get_system_info()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Operating System", sys_info["os"])
            st.metric("CPU", sys_info["cpu"])
        with col2:
            st.metric("Architecture", sys_info["architecture"])
            st.metric("RAM", sys_info["ram"])
        with col3:
            st.metric("Available Disk Space", sys_info["disk_space"])

    # OS Selection
    st.markdown("### Select Your Operating System")
    
    tabs = st.tabs([f"{data['icon']} {os_name}" for os_name, data in installer.os_data.items()])
    
    for tab, (os_name, data) in zip(tabs, installer.os_data.items()):
        with tab:
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.markdown(f"### {os_name} Versions")
                version = st.selectbox(
                    "Choose Version",
                    options=list(data["versions"].keys()),
                    key=f"version_{os_name}"
                )
            
            with col2:
                st.markdown("### Installation Options")
                
                # Show note for specific OS
                if "note" in data:
                    st.info(data["note"])
                
                # Verify download link
                url = data["versions"][version]["url"]
                is_valid, status_message = installer.verify_download_link(url)
                
                if is_valid:
                    st.success("✅ Download link available")
                    
                    download_path = st.text_input(
                        "Download Path",
                        value=str(Path.home() / "Downloads"),
                        key=f"path_{os_name}"
                    )
                    
                    if st.button("Download and Install", key=f"install_{os_name}"):
                        try:
                            os_info = data["versions"][version]
                            destination = os.path.join(download_path, f"{os_name}_{version}.iso")
                            
                            # Special handling for Windows
                            if os_name == "Windows":
                                st.info("Opening Windows download page in your browser...")
                                st.markdown(f"[Click here to download {version}]({os_info['url']})")
                                st.markdown(data["note"])
                                continue
                                
                            # Special handling for Zorin OS
                            if os_name == "Zorin OS":
                                st.info("Opening Zorin OS download page in your browser...")
                                st.markdown(f"[Click here to download {version}]({os_info['url']})")
                                continue
                            
                            with st.spinner(f"Downloading {os_name} {version}..."):
                                if installer.download_os(os_info["url"], destination):
                                    if os.path.exists(destination):
                                        if installer.verify_checksum(destination, os_info["checksum"]):
                                            st.success(f"✅ {os_name} {version} downloaded successfully!")
                                            st.info("Follow the installation instructions in your system's boot menu.")
                                        else:
                                            st.warning("⚠️ Download completed but checksum verification failed. The file might be corrupted.")
                                    else:
                                        st.error("❌ Download failed - file not found")
                        except Exception as e:
                            st.error(f"Error during download: {str(e)}")
                else:
                    st.error(f"❌ Download currently unavailable: {status_message}")
                    st.warning("""
                    🛠️ Maintenance Notice
                    
                    This download is currently unavailable. This might be due to:
                    - Temporary server maintenance
                    - Link updates in progress
                    - Recent version changes
                    
                    Please try again later or check the official website:
                    """)
                    
                    # Add official website links based on OS
                    official_links = {
                        "Ubuntu": "https://ubuntu.com/download",
                        "Fedora": "https://fedoraproject.org/workstation/download",
                        "Debian": "https://www.debian.org/download",
                        "Linux Mint": "https://linuxmint.com/download.php",
                        "Pop!_OS": "https://pop.system76.com",
                        "Manjaro": "https://manjaro.org/download",
                        "Zorin OS": "https://zorin.com/os/download",
                        "elementary OS": "https://elementary.io",
                        "Kali Linux": "https://www.kali.org/get-kali",
                        "Windows": "https://www.microsoft.com/software-download"
                    }
                    
                    if os_name in official_links:
                        st.markdown(f"[Official {os_name} Download Page]({official_links[os_name]})")

if __name__ == "__main__":
    main()
