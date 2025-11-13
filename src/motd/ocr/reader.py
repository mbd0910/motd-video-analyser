"""OCR reader for extracting text from video frames."""

import easyocr
import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class OCRReader:
    """Reads text from video frames using EasyOCR."""

    def __init__(self, config: Dict):
        """
        Initialise OCR reader.

        Args:
            config: OCR configuration dict with:
                - languages: List of language codes (e.g., ['en'])
                - gpu: Whether to use GPU (bool)
                - confidence_threshold: Minimum confidence (float)
                - regions: Dict of region definitions
        """
        self.config = config

        # Initialise EasyOCR reader
        gpu_enabled = config.get('gpu', True)
        logger.info(f"Initialising EasyOCR with GPU={'enabled' if gpu_enabled else 'disabled'}")

        self.reader = easyocr.Reader(
            config['languages'],
            gpu=gpu_enabled
        )

        self.confidence_threshold = config.get('confidence_threshold', 0.7)
        self.regions = config.get('regions', {})

        logger.info(
            f"OCR reader initialised with {len(self.regions)} regions, "
            f"confidence threshold: {self.confidence_threshold}"
        )

    def extract_region(
        self,
        frame_path: Path,
        region_name: str
    ) -> List[Dict]:
        """
        Extract text from a specific region of a frame.

        Args:
            frame_path: Path to frame image
            region_name: Name of region ('ft_score', 'scoreboard', or 'formation')

        Returns:
            List of dicts with:
                - text: Extracted text
                - confidence: OCR confidence score
                - bbox: Bounding box coordinates
                - region: Region name

        Raises:
            ValueError: If frame cannot be loaded or region is unknown
        """
        # Load frame
        try:
            frame = cv2.imread(str(frame_path))
            if frame is None:
                raise ValueError(f"Could not load frame: {frame_path}")
        except Exception as e:
            raise ValueError(f"Could not load frame: {frame_path}") from e

        # Get region coordinates
        if region_name not in self.regions:
            raise ValueError(
                f"Unknown region: {region_name}. "
                f"Available regions: {list(self.regions.keys())}"
            )

        region = self.regions[region_name]
        x, y, w, h = region['x'], region['y'], region['width'], region['height']

        # Crop to region
        cropped = frame[y:y+h, x:x+w]

        # Run OCR
        logger.debug(f"Running OCR on {region_name} region of {frame_path.name}")
        results = self.reader.readtext(cropped)

        # Format results
        formatted = []
        for bbox, text, conf in results:
            if conf >= self.confidence_threshold:
                formatted.append({
                    'text': text,
                    'confidence': conf,
                    'bbox': bbox,
                    'region': region_name
                })
                logger.debug(
                    f"  Extracted from {region_name}: '{text}' "
                    f"(confidence: {conf:.2f})"
                )

        return formatted

    def extract_ft_score(self, frame_path: Path) -> List[Dict]:
        """
        Extract text from full-time score region (lower-middle).

        This is the PRIMARY target region for team name extraction.
        Expected accuracy: 90-95% auto-capture rate.

        Args:
            frame_path: Path to frame image

        Returns:
            List of OCR results from the FT score region
        """
        return self.extract_region(frame_path, 'ft_score')

    def extract_scoreboard(self, frame_path: Path) -> List[Dict]:
        """
        Extract text from scoreboard region (top-left).

        This is the SECONDARY target region for team name extraction.
        Expected accuracy: 75-85% (ubiquitous but often motion-blurred).

        Args:
            frame_path: Path to frame image

        Returns:
            List of OCR results from the scoreboard region
        """
        return self.extract_region(frame_path, 'scoreboard')

    def extract_formation(self, frame_path: Path) -> List[Dict]:
        """
        Extract text from formation graphic region (bottom-right).

        This is the VALIDATION target region for ground truth comparison.
        Note: Only auto-captured for 3-4 of 7 matches, primarily use manual screenshots.

        Args:
            frame_path: Path to frame image

        Returns:
            List of OCR results from the formation region
        """
        return self.extract_region(frame_path, 'formation')

    def extract_all_regions(self, frame_path: Path) -> Dict[str, List[Dict]]:
        """
        Extract text from all defined regions.

        Args:
            frame_path: Path to frame image

        Returns:
            Dict mapping region names to extraction results.
            On error for a region, returns [{'error': str(e)}] to enable
            fallback to other regions without crashing the pipeline.
        """
        results = {}
        for region_name in self.regions.keys():
            try:
                results[region_name] = self.extract_region(frame_path, region_name)
            except Exception as e:
                # Log error but continue with other regions
                logger.warning(
                    f"Error extracting region {region_name} from {frame_path.name}: {e}"
                )
                results[region_name] = [{'error': str(e)}]

        return results

    def extract_with_fallback(self, frame_path: Path) -> Dict:
        """
        Extract text using multi-tiered strategy: FT score → scoreboard → formation.

        Uses fallback logic based on reconnaissance findings:
        1. Try FT score region (PRIMARY - 90-95% accuracy)
        2. If insufficient results, try scoreboard (SECONDARY - 75-85% accuracy)
        3. Formation region for validation only (manual screenshots)

        Args:
            frame_path: Path to frame image

        Returns:
            Dict with:
                - primary_source: Which region provided the results ('ft_score', 'scoreboard', or 'none')
                - results: List of OCR results
                - all_regions: Dict of all region results (for debugging)
        """
        all_results = self.extract_all_regions(frame_path)

        # Try FT score first (PRIMARY)
        ft_score_results = all_results.get('ft_score', [])
        if ft_score_results and not any('error' in r for r in ft_score_results):
            return {
                'primary_source': 'ft_score',
                'results': ft_score_results,
                'all_regions': all_results
            }

        # Fall back to scoreboard (SECONDARY)
        scoreboard_results = all_results.get('scoreboard', [])
        if scoreboard_results and not any('error' in r for r in scoreboard_results):
            logger.debug(
                f"FT score region yielded no results for {frame_path.name}, "
                f"using scoreboard fallback"
            )
            return {
                'primary_source': 'scoreboard',
                'results': scoreboard_results,
                'all_regions': all_results
            }

        # No usable results from either region
        logger.debug(
            f"No usable OCR results from primary regions for {frame_path.name}"
        )
        return {
            'primary_source': 'none',
            'results': [],
            'all_regions': all_results
        }
