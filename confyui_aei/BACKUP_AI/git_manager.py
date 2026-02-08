"""Git repository manager for cloning and updating repositories."""

import asyncio
import os
import subprocess
from pathlib import Path

from config import GitRepoConfig
from utils import logger, run_command


class Git:
    """Manages Git repository operations."""
    
    def __init__(self, python_path: Path, custom_nodes_dir: Path):
        """Initialize Git manager.
        
        Args:
            python_path: Path to python.exe for installing dependencies
            custom_nodes_dir: Base directory for custom nodes
        """
        self.python_path = Path(python_path)
        self.custom_nodes_dir = Path(custom_nodes_dir)
        self.custom_nodes_dir.mkdir(parents=True, exist_ok=True)
    
    async def clone(
        self,
        url: str,
        dest_folder: str,
        *,
        skip_lfs: bool = True,
        install_deps: bool = True
    ) -> Path:
        """Clone a Git repository.
        
        Args:
            url: Git repository URL
            dest_folder: Destination folder name (relative to custom_nodes_dir)
            skip_lfs: Skip LFS files (faster cloning)
            install_deps: Install dependencies after cloning
            
        Returns:
            Path to cloned repository
        """
        dest_path = self.custom_nodes_dir / dest_folder
        
        if dest_path.exists():
            logger.info(f"Repository already exists: {dest_folder}")
            return dest_path
        
        logger.info(f"Cloning {dest_folder}")
        
        env = os.environ.copy()
        if skip_lfs:
            env['GIT_LFS_SKIP_SMUDGE'] = '1'
        
        # Run git clone in a thread pool to make it async
        await asyncio.to_thread(
            run_command,
            ["git", "clone", url, str(dest_path)],
            env=env
        )
        
        if install_deps:
            await self.install_dependencies(dest_path)
        
        return dest_path
    
    async def clone_multiple(
        self,
        repos: list[GitRepoConfig],
        *,
        skip_lfs: bool = True,
        install_deps: bool = True,
        max_parallel: int = 5
    ) -> list[Path]:
        """Clone multiple repositories in parallel.
        
        Args:
            repos: List of repository configurations
            skip_lfs: Skip LFS files
            install_deps: Install dependencies after cloning
            max_parallel: Maximum number of parallel clone operations
            
        Returns:
            List of paths to cloned repositories
        """
        semaphore = asyncio.Semaphore(max_parallel)
        
        async def clone_with_semaphore(repo: GitRepoConfig) -> Path:
            async with semaphore:
                return await self.clone(
                    repo.url,
                    repo.dest_folder,
                    skip_lfs=skip_lfs,
                    install_deps=install_deps
                )
        
        tasks = [clone_with_semaphore(repo) for repo in repos]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and log them
        paths = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to clone {repos[i].dest_folder}: {result}")
            else:
                paths.append(result)
        
        return paths
    
    def update(self, repo_path: Path, branch: str = "master") -> None:
        """Update repository to latest version.
        
        Args:
            repo_path: Path to repository
            branch: Branch to checkout (default: master)
        """
        if not repo_path.exists():
            logger.warning(f"Repository not found: {repo_path}")
            return
        
        logger.info(f"Updating {repo_path.name}")
        
        try:
            # Checkout branch
            run_command(
                ["git", "checkout", branch, "-q"],
                cwd=repo_path
            )
            
            # Pull latest changes
            run_command(
                ["git", "pull"],
                cwd=repo_path
            )
        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to update {repo_path.name}: {e}")
    
    def checkout_tag(self, repo_path: Path, tag: str) -> None:
        """Checkout a specific tag.
        
        Args:
            repo_path: Path to repository
            tag: Tag to checkout
        """
        if not repo_path.exists():
            logger.warning(f"Repository not found: {repo_path}")
            return
        
        logger.info(f"Checking out tag {tag} in {repo_path.name}")
        
        run_command(
            ["git", "checkout", tag, "-q"],
            cwd=repo_path
        )
    
    async def install_dependencies(self, repo_path: Path) -> None:
        """Install dependencies for a repository.
        
        Checks for requirements.txt and install.py and runs them if present.
        
        Args:
            repo_path: Path to repository
        """
        # Check for requirements.txt
        requirements_file = repo_path / "requirements.txt"
        if requirements_file.exists() and requirements_file.stat().st_size > 0:
            logger.info(f"Installing requirements from {repo_path.name}")
            
            await asyncio.to_thread(
                run_command,
                [
                    str(self.python_path),
                    "-I",
                    "-m",
                    "uv",
                    "pip",
                    "install",
                    "-r",
                    str(requirements_file),
                    "--no-cache",
                    "--link-mode=copy"
                ]
            )
        
        # Check for install.py
        install_script = repo_path / "install.py"
        if install_script.exists() and install_script.stat().st_size > 0:
            logger.info(f"Running install.py from {repo_path.name}")
            
            await asyncio.to_thread(
                run_command,
                [str(self.python_path), "-I", str(install_script)],
                cwd=repo_path
            )
    
    def get_tags(self, repo_path: Path, limit: int = 5) -> list[str]:
        """Get recent tags from repository.
        
        Args:
            repo_path: Path to repository
            limit: Maximum number of tags to return
            
        Returns:
            List of tag names
        """
        if not repo_path.exists():
            return []
        
        result = run_command(
            ["git", "tag", "--sort=-creatordate"],
            cwd=repo_path,
            check=False
        )
        
        if result.returncode != 0:
            return []
        
        tags = result.stdout.strip().split('\n')
        return [tag for tag in tags if tag][:limit]
    
    def is_detached(self, repo_path: Path) -> bool:
        """Check if repository is in detached HEAD state.
        
        Args:
            repo_path: Path to repository
            
        Returns:
            True if in detached HEAD state
        """
        if not repo_path.exists():
            return False
        
        result = run_command(
            ["git", "symbolic-ref", "-q", "HEAD"],
            cwd=repo_path,
            check=False
        )
        
        return result.returncode != 0
