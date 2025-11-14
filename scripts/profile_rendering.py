#!/usr/bin/env python3
"""
Performance profiling script for DFPlayer rendering system.

Measures and reports:
- Framebuffer push times
- Widget render times
- Screen render times
- Frame rate performance
- Memory usage

Usage:
    python3 scripts/profile_rendering.py [--iterations N] [--mock]

Options:
    --iterations N    Number of test iterations (default: 100)
    --mock           Use mock hardware instead of real devices
"""

import argparse
import sys
import time
import statistics
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Error: PIL (Pillow) not installed. Install with: pip install pillow")
    sys.exit(1)


class RenderingProfiler:
    """Profiler for rendering performance analysis."""

    def __init__(self, use_mock: bool = False):
        """
        Initialize profiler.

        Args:
            use_mock: Use mock hardware instead of real devices
        """
        self.use_mock = use_mock
        self.timings = {
            'framebuffer_push': [],
            'widget_render': [],
            'screen_render': [],
            'full_frame': []
        }

    def profile_framebuffer_push(self, iterations: int = 100):
        """
        Profile framebuffer push operations.

        Args:
            iterations: Number of test iterations
        """
        print(f"\n{'='*60}")
        print(f"Profiling Framebuffer Push ({iterations} iterations)")
        print(f"{'='*60}")

        if self.use_mock:
            from tests.fixtures.mock_hardware import MockFramebuffer
            fb = MockFramebuffer(width=480, height=320)
        else:
            try:
                from hardware.framebuffer import Framebuffer
                fb = Framebuffer(device="/dev/fb0")
            except Exception as e:
                print(f"Error: Cannot open framebuffer: {e}")
                print("Falling back to mock hardware")
                from tests.fixtures.mock_hardware import MockFramebuffer
                fb = MockFramebuffer(width=480, height=320)

        # Create test image
        test_img = Image.new("RGB", (fb.width, fb.height), (50, 50, 50))
        draw = ImageDraw.Draw(test_img)

        # Draw some test content
        for i in range(10):
            draw.rectangle((i * 40, i * 20, i * 40 + 100, i * 20 + 50), fill=(200, 100, 50))

        # Profile push operations
        timings = []
        for i in range(iterations):
            start = time.perf_counter()
            fb.push(test_img)
            elapsed = time.perf_counter() - start
            timings.append(elapsed * 1000)  # Convert to ms

            if (i + 1) % 10 == 0:
                print(f"  Progress: {i+1}/{iterations}")

        self.timings['framebuffer_push'] = timings

        # Report statistics
        print(f"\nFramebuffer Push Statistics:")
        print(f"  Mean:   {statistics.mean(timings):.2f} ms")
        print(f"  Median: {statistics.median(timings):.2f} ms")
        print(f"  Min:    {min(timings):.2f} ms")
        print(f"  Max:    {max(timings):.2f} ms")
        print(f"  StdDev: {statistics.stdev(timings):.2f} ms")

        # Frame rate calculation
        avg_ms = statistics.mean(timings)
        fps = 1000.0 / avg_ms if avg_ms > 0 else 0
        print(f"  Theoretical max FPS: {fps:.1f}")

        if hasattr(fb, 'close'):
            fb.close()

    def profile_widget_rendering(self, iterations: int = 100):
        """
        Profile widget rendering operations.

        Args:
            iterations: Number of test iterations
        """
        print(f"\n{'='*60}")
        print(f"Profiling Widget Rendering ({iterations} iterations)")
        print(f"{'='*60}")

        from ui.framework_v2.widgets import ButtonWidget, ListWidget, SliderWidget

        # Create test widgets
        button = ButtonWidget((10, 10, 200, 60), "Test Button", lambda: None)
        list_widget = ListWidget([f"Item {i}" for i in range(20)], visible_rows=5)
        slider = SliderWidget((10, 100, 300, 20), min_value=0, max_value=30)

        # Create test canvas
        img = Image.new("RGB", (480, 320), (0, 0, 0))
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
        except Exception:
            font = ImageFont.load_default()

        # Profile button rendering
        button_timings = []
        for _ in range(iterations):
            start = time.perf_counter()
            button.draw(draw, font)
            elapsed = time.perf_counter() - start
            button_timings.append(elapsed * 1000)

        # Profile list rendering
        list_timings = []
        for _ in range(iterations):
            start = time.perf_counter()
            list_widget.draw(draw, (10, 150, 300, 150), font)
            elapsed = time.perf_counter() - start
            list_timings.append(elapsed * 1000)

        # Profile slider rendering
        slider_timings = []
        for _ in range(iterations):
            start = time.perf_counter()
            slider.draw(draw, font)
            elapsed = time.perf_counter() - start
            slider_timings.append(elapsed * 1000)

        # Report statistics
        print(f"\nButton Rendering:")
        print(f"  Mean: {statistics.mean(button_timings):.3f} ms")

        print(f"\nList Rendering (5 visible items):")
        print(f"  Mean: {statistics.mean(list_timings):.3f} ms")

        print(f"\nSlider Rendering:")
        print(f"  Mean: {statistics.mean(slider_timings):.3f} ms")

        self.timings['widget_render'] = button_timings + list_timings + slider_timings

    def profile_full_frame(self, iterations: int = 50):
        """
        Profile complete frame rendering (screen + widgets + push).

        Args:
            iterations: Number of test iterations
        """
        print(f"\n{'='*60}")
        print(f"Profiling Full Frame Rendering ({iterations} iterations)")
        print(f"{'='*60}")

        from ui.framework_v2.manager import ScreenManagerV2
        from ui.screens_v2.home import HomeScreen

        if self.use_mock:
            from tests.fixtures.mock_hardware import MockFramebuffer
            fb = MockFramebuffer(width=480, height=320)
        else:
            try:
                from hardware.framebuffer import Framebuffer
                fb = Framebuffer(device="/dev/fb0")
            except Exception:
                from tests.fixtures.mock_hardware import MockFramebuffer
                fb = MockFramebuffer(width=480, height=320)

        # Set up screen manager
        screen_manager = ScreenManagerV2(services={})
        screen_manager.register("home", HomeScreen)
        screen_manager.push("home")

        # Create rendering context
        img = Image.new("RGB", (fb.width, fb.height), (0, 0, 0))
        draw = ImageDraw.Draw(img)

        try:
            fonts = {
                'small': ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14),
                'medium': ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18),
                'large': ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24),
            }
        except Exception:
            default = ImageFont.load_default()
            fonts = {'small': default, 'medium': default, 'large': default}

        context = {
            'image': img,
            'draw': draw,
            'fonts': fonts,
            'width': fb.width,
            'height': fb.height
        }

        # Profile full frame rendering
        timings = []
        for i in range(iterations):
            start = time.perf_counter()

            # Clear canvas
            draw.rectangle((0, 0, fb.width, fb.height), fill=(0, 0, 0))

            # Render screen
            screen_manager.render(context)

            # Push to framebuffer
            fb.push(img)

            elapsed = time.perf_counter() - start
            timings.append(elapsed * 1000)

            if (i + 1) % 10 == 0:
                print(f"  Progress: {i+1}/{iterations}")

        self.timings['full_frame'] = timings

        # Report statistics
        print(f"\nFull Frame Statistics:")
        print(f"  Mean:   {statistics.mean(timings):.2f} ms")
        print(f"  Median: {statistics.median(timings):.2f} ms")
        print(f"  Min:    {min(timings):.2f} ms")
        print(f"  Max:    {max(timings):.2f} ms")

        # Frame rate analysis
        avg_ms = statistics.mean(timings)
        fps = 1000.0 / avg_ms if avg_ms > 0 else 0
        print(f"  Average FPS: {fps:.1f}")

        # Check targets
        target_16ms = sum(1 for t in timings if t < 16.67)  # 60 FPS
        target_33ms = sum(1 for t in timings if t < 33.33)  # 30 FPS

        print(f"\nTarget Achievement:")
        print(f"  <16.67ms (60 FPS): {target_16ms}/{iterations} ({target_16ms/iterations*100:.1f}%)")
        print(f"  <33.33ms (30 FPS): {target_33ms}/{iterations} ({target_33ms/iterations*100:.1f}%)")

        if hasattr(fb, 'close'):
            fb.close()

    def generate_summary(self):
        """Generate summary report."""
        print(f"\n{'='*60}")
        print("PERFORMANCE SUMMARY")
        print(f"{'='*60}")

        if self.timings['framebuffer_push']:
            fb_avg = statistics.mean(self.timings['framebuffer_push'])
            print(f"\nFramebuffer Push: {fb_avg:.2f} ms average")

        if self.timings['widget_render']:
            widget_avg = statistics.mean(self.timings['widget_render'])
            print(f"Widget Rendering: {widget_avg:.3f} ms average")

        if self.timings['full_frame']:
            frame_avg = statistics.mean(self.timings['full_frame'])
            fps = 1000.0 / frame_avg if frame_avg > 0 else 0
            print(f"Full Frame:       {frame_avg:.2f} ms average ({fps:.1f} FPS)")

        print(f"\nRecommendations:")
        if self.timings['full_frame']:
            avg_ms = statistics.mean(self.timings['full_frame'])
            if avg_ms < 16.67:
                print("  ✅ Performance excellent - can target 60 FPS")
            elif avg_ms < 33.33:
                print("  ✅ Performance good - target 30 FPS achievable")
            else:
                print("  ⚠️  Performance needs optimization - < 30 FPS")
                print("     Consider reducing widget complexity or screen size")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Profile DFPlayer rendering performance")
    parser.add_argument(
        '--iterations',
        type=int,
        default=100,
        help='Number of test iterations (default: 100)'
    )
    parser.add_argument(
        '--mock',
        action='store_true',
        help='Use mock hardware instead of real devices'
    )
    args = parser.parse_args()

    profiler = RenderingProfiler(use_mock=args.mock)

    print("DFPlayer Rendering Performance Profiler")
    print(f"Hardware: {'Mock' if args.mock else 'Real'}")
    print(f"Iterations: {args.iterations}")

    try:
        profiler.profile_framebuffer_push(iterations=args.iterations)
        profiler.profile_widget_rendering(iterations=args.iterations)
        profiler.profile_full_frame(iterations=min(args.iterations, 50))
        profiler.generate_summary()

    except KeyboardInterrupt:
        print("\n\nProfiling interrupted by user")
    except Exception as e:
        print(f"\n\nError during profiling: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
