"""EnergyPlus simulation runner with batch processing capabilities."""

import subprocess
import shutil
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from tqdm import tqdm

from core.config import get_config


logger = logging.getLogger(__name__)


@dataclass
class SimulationResult:
    """Container for simulation results."""

    success: bool
    idf_path: Path
    output_dir: Path
    execution_time: float
    error_message: Optional[str] = None
    sql_file: Optional[Path] = None
    csv_files: List[Path] = None

    def __post_init__(self):
        if self.csv_files is None:
            self.csv_files = []


class EnergyPlusRunner:
    """Manages EnergyPlus simulation execution."""

    def __init__(self, config=None):
        """Initialize the runner.

        Args:
            config: Configuration object. If None, uses global config.
        """
        self.config = config or get_config()
        self.energyplus_exe = self.config.energyplus.get_executable_path()

        if not self.energyplus_exe.exists():
            raise FileNotFoundError(
                f"EnergyPlus executable not found at: {self.energyplus_exe}\n"
                "Please install EnergyPlus or set the correct path in config."
            )

        # ExpandObjects executable (in same directory as EnergyPlus)
        self.expand_objects_exe = self.energyplus_exe.parent / "ExpandObjects.exe"
        if not self.expand_objects_exe.exists():
            # Try without .exe extension (Linux/Mac)
            self.expand_objects_exe = self.energyplus_exe.parent / "ExpandObjects"

        logger.info(f"EnergyPlus executable found: {self.energyplus_exe}")
        if self.expand_objects_exe.exists():
            logger.info(f"ExpandObjects found: {self.expand_objects_exe}")

    def _needs_expand_objects(self, idf_path: Path) -> bool:
        """Check if IDF file contains HVACTemplate objects that need expansion."""
        try:
            with open(idf_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            return 'HVACTemplate:' in content
        except Exception as e:
            logger.warning(f"Could not check IDF for HVACTemplate objects: {e}")
            return False

    def _run_expand_objects(self, idf_path: Path, output_dir: Path) -> Optional[Path]:
        """Run ExpandObjects preprocessor on IDF file.

        Args:
            idf_path: Path to original IDF file
            output_dir: Output directory for expanded IDF

        Returns:
            Path to expanded IDF file, or None if expansion failed
        """
        if not self.expand_objects_exe.exists():
            logger.error("ExpandObjects not found - cannot expand HVACTemplate objects")
            return None

        logger.info("Running ExpandObjects to expand HVACTemplate objects...")

        # Ensure absolute paths
        idf_path = idf_path.resolve()
        output_dir = output_dir.resolve()

        # Copy IDF to output directory (ExpandObjects expects in.idf)
        in_idf = output_dir / "in.idf"
        try:
            shutil.copy(str(idf_path), str(in_idf))
            logger.info(f"Copied IDF to: {in_idf}")
        except Exception as e:
            logger.error(f"Could not copy IDF: {e}")
            return None

        # Also need Energy+.idd in same directory
        idd_file = self.energyplus_exe.parent / "Energy+.idd"
        if idd_file.exists():
            try:
                shutil.copy(str(idd_file), str(output_dir / "Energy+.idd"))
                logger.info("Copied Energy+.idd")
            except Exception as e:
                logger.warning(f"Could not copy IDD file: {e}")

        try:
            # Run ExpandObjects (it reads in.idf and creates expanded.idf)
            # Use absolute path and shell=True for Windows compatibility
            import platform
            use_shell = platform.system() == "Windows"

            logger.info(f"Running: {self.expand_objects_exe}")
            logger.info(f"Working directory: {output_dir}")

            result = subprocess.run(
                [str(self.expand_objects_exe.resolve())],
                cwd=str(output_dir),
                capture_output=True,
                text=True,
                timeout=60,
                shell=use_shell
            )

            logger.info(f"ExpandObjects return code: {result.returncode}")
            if result.stdout:
                logger.info(f"ExpandObjects stdout: {result.stdout}")
            if result.stderr:
                logger.warning(f"ExpandObjects stderr: {result.stderr}")

            # Check for expanded.idf
            expanded_idf = output_dir / "expanded.idf"
            if expanded_idf.exists():
                logger.info(f"ExpandObjects completed successfully: {expanded_idf}")
                return expanded_idf
            else:
                logger.error("ExpandObjects did not create expanded.idf")
                logger.error(f"Files in output dir: {list(output_dir.glob('*'))}")
                return None

        except subprocess.TimeoutExpired:
            logger.error("ExpandObjects timed out")
            return None
        except Exception as e:
            logger.error(f"ExpandObjects error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def run_simulation(
        self,
        idf_path: Path | str,
        weather_file: Path | str,
        output_dir: Optional[Path | str] = None,
        output_prefix: str = "eplus",
    ) -> SimulationResult:
        """Run a single EnergyPlus simulation.

        Args:
            idf_path: Path to IDF file
            weather_file: Path to EPW weather file
            output_dir: Directory for output files
            output_prefix: Prefix for output files

        Returns:
            SimulationResult object with execution details
        """
        idf_path = Path(idf_path)
        weather_file = Path(weather_file)

        if not idf_path.exists():
            return SimulationResult(
                success=False,
                idf_path=idf_path,
                output_dir=Path(),
                execution_time=0,
                error_message=f"IDF file not found: {idf_path}",
            )

        if not weather_file.exists():
            return SimulationResult(
                success=False,
                idf_path=idf_path,
                output_dir=Path(),
                execution_time=0,
                error_message=f"Weather file not found: {weather_file}",
            )

        # Setup output directory
        if output_dir is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = Path(self.config.simulation.output_dir) / f"sim_{timestamp}"

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Running simulation: {idf_path.name}")
        logger.info(f"Weather file: {weather_file.name}")
        logger.info(f"Output directory: {output_dir}")

        # Check if ExpandObjects is needed (HVACTemplate objects present)
        if self._needs_expand_objects(idf_path):
            logger.info("IDF contains HVACTemplate objects - running ExpandObjects")
            expanded_idf = self._run_expand_objects(idf_path, output_dir)

            if expanded_idf is None:
                return SimulationResult(
                    success=False,
                    idf_path=idf_path,
                    output_dir=output_dir,
                    execution_time=0,
                    error_message="ExpandObjects failed - could not expand HVACTemplate objects",
                )

            # Use expanded IDF for simulation
            idf_path = expanded_idf
            logger.info(f"Using expanded IDF: {idf_path.name}")

        # Prepare EnergyPlus command
        cmd = [
            str(self.energyplus_exe),
            "--weather", str(weather_file.absolute()),
            "--output-directory", str(output_dir.absolute()),
            "--output-prefix", output_prefix,
            str(idf_path.absolute()),
        ]

        logger.info("="*80)
        logger.info("ENERGYPLUS COMMAND")
        logger.info("="*80)
        logger.info(f"Executable: {self.energyplus_exe}")
        logger.info(f"Working dir: {output_dir}")
        logger.info(f"IDF file: {idf_path}")
        logger.info(f"Weather file: {weather_file}")
        logger.info(f"Full command: {' '.join(cmd)}")
        logger.info("="*80)

        start_time = datetime.now()
        try:
            # Run EnergyPlus
            logger.info("Starting EnergyPlus subprocess...")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.simulation.timeout,
                cwd=str(output_dir.absolute()),
            )
            logger.info("EnergyPlus subprocess completed.")

            execution_time = (datetime.now() - start_time).total_seconds()

            # Log EnergyPlus output
            logger.info(f"EnergyPlus return code: {result.returncode}")
            logger.info(f"EnergyPlus execution time: {execution_time:.2f}s")

            if result.stdout:
                logger.info(f"EnergyPlus stdout (first 2000 chars):\n{result.stdout[:2000]}")
            else:
                logger.warning("EnergyPlus stdout is EMPTY")

            if result.stderr:
                logger.warning(f"EnergyPlus stderr:\n{result.stderr}")
            else:
                logger.info("EnergyPlus stderr is empty (normal)")

            # Check for errors
            err_file = output_dir / f"{output_prefix}out.err"

            # Log err file info for debugging
            if err_file.exists():
                err_size = err_file.stat().st_size
                logger.info(f"Error file size: {err_size} bytes")
                if err_size == 0:
                    logger.warning("ERROR FILE IS EMPTY (0 bytes) - This is unusual!")
                    logger.warning("EnergyPlus should always write to the error file.")
                    logger.warning("Check: 1) Was EnergyPlus actually executed? 2) File permissions? 3) Disk space?")
            else:
                logger.warning(f"Error file does not exist: {err_file}")

            success = self._check_simulation_success(err_file)

            # Collect output files
            sql_file = output_dir / f"{output_prefix}out.sql"
            csv_files = list(output_dir.glob("*.csv"))

            # Log SQL file info
            if sql_file.exists():
                sql_size = sql_file.stat().st_size
                logger.info(f"SQL file size: {sql_size:,} bytes")
                if sql_size < 500_000:  # Less than 500KB is suspiciously small for annual simulation
                    logger.warning(f"SQL file is very small ({sql_size:,} bytes) - Expected >1MB for annual simulation")

            if not success:
                error_msg = self._extract_error_message(err_file)
                logger.error(f"Simulation failed: {error_msg}")
            else:
                logger.info(f"Simulation completed successfully in {execution_time:.2f}s")

            # Clean up intermediate files if configured
            if not self.config.simulation.keep_intermediate_files:
                self._cleanup_intermediate_files(output_dir, output_prefix)

            return SimulationResult(
                success=success,
                idf_path=idf_path,
                output_dir=output_dir,
                execution_time=execution_time,
                error_message=None if success else error_msg,
                sql_file=sql_file if sql_file.exists() else None,
                csv_files=csv_files,
            )

        except subprocess.TimeoutExpired:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Simulation timed out after {execution_time:.2f}s")
            return SimulationResult(
                success=False,
                idf_path=idf_path,
                output_dir=output_dir,
                execution_time=execution_time,
                error_message="Simulation timed out",
            )

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Simulation error: {str(e)}")
            return SimulationResult(
                success=False,
                idf_path=idf_path,
                output_dir=output_dir,
                execution_time=execution_time,
                error_message=str(e),
            )

    def run_batch(
        self,
        simulations: List[Dict[str, Any]],
        parallel: bool = True,
    ) -> List[SimulationResult]:
        """Run multiple simulations in batch.

        Args:
            simulations: List of simulation configurations, each containing:
                - idf_path: Path to IDF file
                - weather_file: Path to EPW weather file
                - output_dir: (optional) Output directory
                - output_prefix: (optional) Output prefix
            parallel: Whether to run simulations in parallel

        Returns:
            List of SimulationResult objects
        """
        logger.info(f"Starting batch simulation: {len(simulations)} simulations")

        if parallel and len(simulations) > 1:
            return self._run_batch_parallel(simulations)
        else:
            return self._run_batch_sequential(simulations)

    def _run_batch_sequential(
        self, simulations: List[Dict[str, Any]]
    ) -> List[SimulationResult]:
        """Run simulations sequentially with progress bar."""
        results = []
        for sim_config in tqdm(simulations, desc="Running simulations"):
            result = self.run_simulation(**sim_config)
            results.append(result)
        return results

    def _run_batch_parallel(
        self, simulations: List[Dict[str, Any]]
    ) -> List[SimulationResult]:
        """Run simulations in parallel using multiprocessing."""
        num_workers = min(self.config.simulation.num_processes, len(simulations))
        logger.info(f"Running {len(simulations)} simulations with {num_workers} workers")

        results = []
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            # Submit all simulations
            future_to_sim = {
                executor.submit(self.run_simulation, **sim_config): sim_config
                for sim_config in simulations
            }

            # Process completed simulations with progress bar
            with tqdm(total=len(simulations), desc="Running simulations") as pbar:
                for future in as_completed(future_to_sim):
                    result = future.result()
                    results.append(result)
                    pbar.update(1)

        # Log summary
        successful = sum(1 for r in results if r.success)
        logger.info(f"Batch complete: {successful}/{len(results)} simulations successful")

        return results

    def _check_simulation_success(self, err_file: Path) -> bool:
        """Check if simulation completed successfully by parsing error file."""
        if not err_file.exists():
            return False

        try:
            with open(err_file, 'r') as f:
                content = f.read()

            # Check for fatal errors first
            if "** Fatal **" in content or "**  Fatal  **" in content:
                return False

            # EnergyPlus writes "EnergyPlus Completed Successfully" on success
            if "EnergyPlus Completed Successfully" in content:
                return True

            # If err file is empty or very small, check for SQL file as success indicator
            # (Sometimes EnergyPlus doesn't write to err file on success)
            if len(content.strip()) < 50:
                sql_file = err_file.parent / "eplusout.sql"
                if sql_file.exists() and sql_file.stat().st_size > 1000:
                    logger.info("Err file empty, but SQL file exists → Success")
                    return True

            return False

        except Exception as e:
            logger.warning(f"Could not read error file: {e}")
            return False

    def _extract_error_message(self, err_file: Path) -> str:
        """Extract error message from EnergyPlus error file."""
        try:
            with open(err_file, 'r') as f:
                lines = f.readlines()

            # Find fatal error lines
            error_lines = [line.strip() for line in lines if "** Fatal **" in line or "**   Fatal   **" in line]

            if error_lines:
                return " ".join(error_lines[:3])  # Return first 3 error lines

            # If no fatal errors, return last 10 lines
            return " ".join(lines[-10:])

        except Exception:
            return "Could not extract error message"

    def _cleanup_intermediate_files(self, output_dir: Path, prefix: str) -> None:
        """Remove intermediate files, keeping only essential outputs."""
        # Files to keep
        keep_extensions = {'.sql', '.csv', '.err', '.htm', '.html', '.idf'}

        for file in output_dir.iterdir():
            if file.is_file() and file.suffix not in keep_extensions:
                try:
                    file.unlink()
                except Exception as e:
                    logger.debug(f"Could not remove {file.name}: {e}")


def main():
    """Command-line entry point for running simulations."""
    import argparse

    parser = argparse.ArgumentParser(description="Run EnergyPlus simulations")
    parser.add_argument("idf_file", help="Path to IDF file")
    parser.add_argument("weather_file", help="Path to EPW weather file")
    parser.add_argument("--output-dir", "-o", help="Output directory")
    parser.add_argument("--config", "-c", help="Path to configuration file")

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Load config if provided
    if args.config:
        from core.config import load_config
        load_config(args.config)

    # Run simulation
    runner = EnergyPlusRunner()
    result = runner.run_simulation(
        idf_path=args.idf_file,
        weather_file=args.weather_file,
        output_dir=args.output_dir,
    )

    if result.success:
        print(f"\nSimulation completed successfully!")
        print(f"Output directory: {result.output_dir}")
        print(f"Execution time: {result.execution_time:.2f}s")
    else:
        print(f"\nSimulation failed!")
        print(f"Error: {result.error_message}")
        exit(1)


if __name__ == "__main__":
    main()
