"""Simple tests to verify the Python installer code."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import GitRepoConfig, PackageConfig, PythonVersionConfig
from utils import logger


def test_imports():
    """Test that all modules can be imported."""
    try:
        import config
        import utils
        import pyembed
        import package_installer
        import git_manager
        import install_comfyui
        import install_addon
        logger.info("✓ All modules imported successfully")
        return True
    except Exception as e:
        logger.error(f"✗ Import failed: {e}")
        return False


def test_config_creation():
    """Test configuration dataclass creation."""
    try:
        # Test GitRepoConfig
        repo = GitRepoConfig(
            url="https://github.com/test/repo",
            dest_folder="test-repo"
        )
        assert repo.url == "https://github.com/test/repo"
        assert repo.dest_folder == "test-repo"
        
        # Test PackageConfig
        pkg = PackageConfig(
            packages=["test==1.0.0"],
            index_url="https://test.com"
        )
        assert pkg.packages == ["test==1.0.0"]
        assert pkg.index_url == "https://test.com"
        
        # Test PythonVersionConfig
        py = PythonVersionConfig(version="3.12.10")
        assert "3.12.10" in py.download_url_computed
        
        logger.info("✓ Configuration dataclasses work correctly")
        return True
    except Exception as e:
        logger.error(f"✗ Config creation failed: {e}")
        return False


def test_utils():
    """Test utility functions."""
    try:
        from utils import ColoredFormatter, setup_logger
        
        # Test logger setup
        test_logger = setup_logger("test")
        assert test_logger is not None
        
        logger.info("✓ Utilities work correctly")
        return True
    except Exception as e:
        logger.error(f"✗ Utils test failed: {e}")
        return False


def test_pyembeder_init():
    """Test PyEmbeder initialization."""
    try:
        from pyembed import PyEmbeder
        
        embedder = PyEmbeder(Path("test_install"))
        assert embedder.base_dir == Path("test_install")
        assert embedder.python_dir == Path("test_install/python_embeded")
        
        logger.info("✓ PyEmbeder initializes correctly")
        return True
    except Exception as e:
        logger.error(f"✗ PyEmbeder init failed: {e}")
        return False


def test_package_installer_init():
    """Test package installer initialization."""
    try:
        from package_installer import PyPip, PyUv, PyInstaller
        
        python_path = Path("test/python.exe")
        
        pip = PyPip(python_path)
        assert pip.python_path == python_path
        
        uv = PyUv(python_path)
        assert uv.python_path == python_path
        
        installer = PyInstaller(python_path)
        assert installer.python_path == python_path
        assert installer.pip is not None
        assert installer.uv is not None
        
        logger.info("✓ Package installers initialize correctly")
        return True
    except Exception as e:
        logger.error(f"✗ Package installer init failed: {e}")
        return False


def test_git_manager_init():
    """Test Git manager initialization."""
    try:
        from git_manager import Git
        
        git = Git(Path("test/python.exe"), Path("test/custom_nodes"))
        assert git.python_path == Path("test/python.exe")
        assert git.custom_nodes_dir == Path("test/custom_nodes")
        
        logger.info("✓ Git manager initializes correctly")
        return True
    except Exception as e:
        logger.error(f"✗ Git manager init failed: {e}")
        return False


def run_all_tests():
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("Running Python Installer Tests")
    logger.info("=" * 60)
    logger.info("")
    
    tests = [
        test_imports,
        test_config_creation,
        test_utils,
        test_pyembeder_init,
        test_package_installer_init,
        test_git_manager_init,
    ]
    
    results = []
    for test in tests:
        logger.info(f"\nRunning {test.__name__}...")
        results.append(test())
    
    logger.info("")
    logger.info("=" * 60)
    passed = sum(results)
    total = len(results)
    logger.info(f"Results: {passed}/{total} tests passed")
    logger.info("=" * 60)
    
    return all(results)


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
