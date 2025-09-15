import os
import numpy as np
import matplotlib.pyplot as plt
import SimpleITK as sitk
import nibabel as nib
from pathlib import Path
from typing import List, Optional, Union
from matplotlib.widgets import Slider

def analyze_vessel_characteristics(segmentations: List[sitk.Image], original_image: sitk.Image) -> dict:
    """
    Analyze vessel characteristics from segmentations to determine appropriate parameters.
    """
    spacing = original_image.GetSpacing()
    vessel_stats = {}
    
    # Analyze each segmentation
    for i, seg in enumerate(segmentations):
        # Get connected components
        cc_filter = sitk.ConnectedComponentImageFilter()
        components = cc_filter.Execute(seg)
        
        # Get component statistics
        stats_filter = sitk.LabelShapeStatisticsImageFilter()
        stats_filter.Execute(components)
        
        # Analyze each component
        volumes_mm3 = []
        diameters_mm = []
        lengths_mm = []
        
        for label in stats_filter.GetLabels():
            # Get physical measurements
            volume_voxels = stats_filter.GetPhysicalSize(label)
            volume_mm3 = volume_voxels * np.prod(spacing)
            
            # Estimate diameter from cross-sectional area
            axis_lengths = stats_filter.GetPrincipalAxes(label)
            major_length = max(axis_lengths) * min(spacing)
            minor_length = min(axis_lengths) * min(spacing)
            
            volumes_mm3.append(volume_mm3)
            diameters_mm.append(minor_length)
            lengths_mm.append(major_length)
        
        vessel_stats[f'seg_{i}'] = {
            'median_volume_mm3': np.median(volumes_mm3),
            'median_diameter_mm': np.median(diameters_mm),
            'median_length_mm': np.median(lengths_mm),
            'min_volume_mm3': np.min(volumes_mm3),
            'min_diameter_mm': np.min(diameters_mm),
            'min_length_mm': np.min(lengths_mm)
        }
    
    # Aggregate statistics across all segmentations
    all_stats = {
        'recommended_radius_mm': np.median([stats['median_diameter_mm']/2 
                                          for stats in vessel_stats.values()]),
        'recommended_min_length_mm': np.median([stats['min_length_mm'] 
                                              for stats in vessel_stats.values()]),
        'recommended_min_volume_mm3': np.median([stats['min_volume_mm3'] 
                                               for stats in vessel_stats.values()]),
        'detailed_stats': vessel_stats
    }
    
    return all_stats

def analyze_gap_sizes(segmentations: List[sitk.Image]) -> dict:
    """
    Analyze gaps between vessel segments to determine appropriate kernel sizes
    """
    gap_stats = {}
    
    for i, seg in enumerate(segmentations):
        # Convert to numpy array for analysis
        seg_array = sitk.GetArrayFromImage(seg)
        
        # Calculate distance transform
        dist_transform = sitk.SignedMaurerDistanceMapImageFilter()
        dist_transform.SetSquaredDistance(False)
        dist_transform.SetUseImageSpacing(True)
        
        # Get distances to nearest vessel
        distances = dist_transform.Execute(seg)
        distances_array = sitk.GetArrayFromImage(distances)
        
        # Analyze only the gaps (negative distances are inside vessels)
        gap_distances = distances_array[distances_array > 0]
        
        if len(gap_distances) > 0:
            gap_stats[f'seg_{i}'] = {
                'median_gap': np.median(gap_distances),
                'min_gap': np.min(gap_distances),
                'max_gap': np.max(gap_distances),
                '25th_percentile': np.percentile(gap_distances, 25),
                '75th_percentile': np.percentile(gap_distances, 75)
            }
    
    # Aggregate statistics
    all_gaps = np.concatenate([gap_distances for seg_array in segmentations])
    overall_stats = {
        'recommended_dilation_radius': np.percentile(all_gaps, 25),  # Conservative
        'recommended_closing_radius': np.median(all_gaps),  # Moderate
        'detailed_stats': gap_stats
    }
    
    return overall_stats

def enhance_vessel_connectivity(
    binary_mask: sitk.Image, 
    original_image: sitk.Image,
    vessel_radius_mm: float = 1.0,
    min_vessel_length_mm: float = 5.0
) -> sitk.Image:
    """
    Enhance vessel connectivity using morphological operations with data-derived parameters
    """
    spacing = original_image.GetSpacing()
    
    # Calculate kernel size from vessel radius
    kernel_radius = int(round(vessel_radius_mm / min(spacing)))
    
    # Calculate minimum object size
    min_vessel_volume_mm3 = np.pi * (vessel_radius_mm**2) * min_vessel_length_mm
    voxel_volume = np.prod(spacing)
    min_object_size = int(min_vessel_volume_mm3 / voxel_volume)
    
    #print(f"\nEnhancement Parameters:")
    #print(f"Kernel radius: {kernel_radius} voxels ({vessel_radius_mm:.2f} mm)")
    #print(f"Minimum object size: {min_object_size} voxels ({min_vessel_volume_mm3:.2f} mm³)")
    
    # Apply morphological operations
    dilate = sitk.BinaryDilateImageFilter()
    dilate.SetKernelRadius(kernel_radius)
    
    erode = sitk.BinaryErodeImageFilter()
    erode.SetKernelRadius(kernel_radius)
    
    connected = dilate.Execute(binary_mask)
    connected = erode.Execute(connected)
    
    components = sitk.ConnectedComponentImageFilter().Execute(connected)
    
    relabel = sitk.RelabelComponentImageFilter()
    relabel.SetMinimumObjectSize(min_object_size)
    final = relabel.Execute(components)
    
    binary_final = sitk.Cast(final > 0, sitk.sitkUInt8)
    binary_final.CopyInformation(original_image)
    
    return binary_final

def preprocess_segmentation(seg: sitk.Image) -> sitk.Image:
    """
    Preprocess segmentation using morphological operations
    """
    # Small dilation to connect nearby vessels
    dilate = sitk.BinaryDilateImageFilter()
    dilate.SetKernelRadius(1)
    
    # Close small gaps
    close = sitk.BinaryMorphologicalClosingImageFilter()
    close.SetKernelRadius(1)
    
    # Apply filters
    processed = dilate.Execute(seg)
    processed = close.Execute(processed)
    
    return sitk.Cast(processed, sitk.sitkUInt8)

def adaptive_staple_threshold_old(consensus_prob: sitk.Image, segmentations: List[sitk.Image]) -> sitk.Image:
    """
    Apply adaptive thresholding based on local vessel properties
    """
    prob_array = sitk.GetArrayFromImage(consensus_prob)
    
    # Calculate local agreement
    vessel_mask = np.zeros_like(prob_array)
    for seg in segmentations:
        vessel_mask += sitk.GetArrayFromImage(seg)
    
    # Lower threshold in regions with high vessel likelihood
    threshold = np.where(vessel_mask > 0, 0.4, 0.6)
    
    # Convert boolean to int array before creating SimpleITK image
    binary = (prob_array > threshold).astype(np.uint8)
    
    return sitk.GetImageFromArray(binary)

def compute_optimal_thresholds(consensus_prob: sitk.Image, segmentations: List[sitk.Image]) -> tuple:
    """
    Compute optimal thresholds based on STAPLE probability distribution
    
    Args:
        consensus_prob: STAPLE probability map
        segmentations: List of input segmentations
    
    Returns:
        tuple: (lower_threshold, higher_threshold)
    """
    prob_array = sitk.GetArrayFromImage(consensus_prob)
    
    # Create vessel mask where any segmentation marked a vessel
    vessel_mask = np.zeros_like(prob_array)
    for seg in segmentations:
        vessel_mask += sitk.GetArrayFromImage(seg)
    vessel_mask = vessel_mask > 0
    
    # Get probabilities in vessel and non-vessel regions
    vessel_probs = prob_array[vessel_mask]
    non_vessel_probs = prob_array[~vessel_mask]
    
    # Compute statistics
    vessel_mean = np.mean(vessel_probs)
    vessel_std = np.std(vessel_probs)
    non_vessel_mean = np.mean(non_vessel_probs)
    non_vessel_std = np.std(non_vessel_probs)
    
    # Compute thresholds
    lower_threshold = vessel_mean - vessel_std
    higher_threshold = non_vessel_mean + non_vessel_std
    
    # print(f"\nThreshold Analysis:")
    # print(f"Vessel region statistics:")
    # print(f"  Mean probability: {vessel_mean:.3f}")
    # print(f"  Standard deviation: {vessel_std:.3f}")
    # print(f"Non-vessel region statistics:")
    # print(f"  Mean probability: {non_vessel_mean:.3f}")
    # print(f"  Standard deviation: {non_vessel_std:.3f}")
    # print(f"Computed thresholds:")
    # print(f"  Lower threshold (vessel regions): {lower_threshold:.3f}")
    # print(f"  Higher threshold (non-vessel regions): {higher_threshold:.3f}")
    
    return lower_threshold, higher_threshold

def adaptive_staple_threshold(consensus_prob: sitk.Image, segmentations: List[sitk.Image]) -> sitk.Image:
    """
    Apply adaptive thresholding based on local vessel properties with computed thresholds
    """
    prob_array = sitk.GetArrayFromImage(consensus_prob)
    
    # Calculate local agreement
    vessel_mask = np.zeros_like(prob_array)
    for seg in segmentations:
        vessel_mask += sitk.GetArrayFromImage(seg)
    vessel_mask = vessel_mask > 0
    
    # Compute optimal thresholds
    lower_thresh, higher_thresh = compute_optimal_thresholds(consensus_prob, segmentations)
    
    # Apply adaptive threshold
    threshold = np.where(vessel_mask, lower_thresh, higher_thresh)
    
    # Convert to binary mask
    binary = (prob_array > threshold).astype(np.uint8)
    
    return sitk.GetImageFromArray(binary)

def plot_img_seg(image: np.ndarray, seg: np.ndarray) -> None:
    """
    Plot image and segmentation side by side.
    """
    return
    for ID in [5, 20, 50, 70, 90]:
        fig, axes = plt.subplots(1, 2, figsize=(10, 5))
        axes[0].imshow(image[ID, ...], cmap='gray')
        axes[0].axis('off')
        axes[0].set_title('Image')
        axes[1].imshow(image[ID, ...], cmap='gray')
        mask = np.ma.masked_where(seg == 0, seg)
        axes[1].imshow(mask[ID,...], alpha=0.8, cmap='autumn')
        axes[1].axis('off')
        axes[1].set_title('Segmentation')
        plt.show()

def plot_img_multiple_seg(image: np.ndarray, segs: List[np.ndarray]) -> None:
    """
    Plot image and multiple segmentations side by side.
    """
    for ID in [5, 20, 50, 70, 90]:
        fig, axes = plt.subplots(1, len(segs) + 1, figsize=(5 * (len(segs) + 1), 5))
        axes[0].imshow(image[ID, ...], cmap='gray')
        axes[0].axis('off')
        axes[0].set_title('Image')
        for i, seg in enumerate(segs, 1):
            axes[i].imshow(image[ID, ...], cmap='gray')
            mask = np.ma.masked_where(seg == 0, seg)
            axes[i].imshow(mask[ID,...], alpha=0.8, cmap='autumn')
            axes[i].axis('off')
            axes[i].set_title(f'Segmentation {i}')
        plt.show()

def verify_spatial_consistency(reference_image: sitk.Image, segmentations: List[sitk.Image], plot_verification: bool = False) -> None:
    """
    Verify that all segmentations match the spatial properties of the reference image.
    Uses a tolerance for floating point comparisons.
    """
    if not segmentations:
        raise ValueError("No segmentations provided")
    
    ref_size = reference_image.GetSize()
    ref_spacing = reference_image.GetSpacing()
    ref_origin = reference_image.GetOrigin()
    ref_direction = reference_image.GetDirection()
    if plot_verification:
        print("Reference image properties:\n")
        print(f"Reference size: {ref_size}")
        print(f"Reference spacing: {ref_spacing}")
        print(f"Reference origin: {ref_origin}")
        print(f"Reference direction: {ref_direction}")
        print("############################################################")
    if len(ref_size) != 3:
        raise ValueError(f"Expected 3D image, but got {len(ref_size)}D")
    
    tolerance = 0.001  # 3 decimal places tolerance
    
    for i, seg in enumerate(segmentations):
        if plot_verification:
            print(f"\nSegmentation {i}")
            print(f"Size: {seg.GetSize()}")
            print(f"Spacing: {seg.GetSpacing()}")
            print(f"Origin: {seg.GetOrigin()}")
            print(f"Direction: {seg.GetDirection()}")
            print("############################################################")
            #plot_img_seg(sitk.GetArrayFromImage(reference_image), sitk.GetArrayFromImage(seg))
        if seg.GetSize() != ref_size:
            raise ValueError(
                f"Segmentation {i} has different dimensions: {seg.GetSize()} vs {ref_size}"
            )
        
        # Compare spacing with tolerance
        if not np.allclose(seg.GetSpacing(), ref_spacing, rtol=tolerance):
            raise ValueError(
                f"Segmentation {i} has different spacing: {np.round(seg.GetSpacing(), 3)} vs {np.round(ref_spacing, 3)}"
            )
        
        # Compare origin with tolerance
        #if not np.allclose(seg.GetOrigin(), ref_origin, rtol=tolerance):
        #    raise ValueError(
        #        f"Segmentation {i} has different origin: {np.round(seg.GetOrigin(), 3)} vs {np.round(ref_origin, 3)}"
        #    )
        
        # Compare direction with tolerance
        #if not np.allclose(seg.GetDirection(), ref_direction, rtol=tolerance):
        #    raise ValueError(
        #        f"Segmentation {i} has different direction: {np.round(seg.GetDirection(), 3)} vs {np.round(ref_direction, 3)}"
        #    )

def verify_segmentation_values(seg: sitk.Image) -> None:
    """
    Verify that the segmentation contains only binary values.
    """
    arr = sitk.GetArrayFromImage(seg)
    unique_values = np.unique(arr)
    if not np.array_equal(unique_values, np.array([0, 1])) and \
       not np.array_equal(unique_values, np.array([0])) and \
       not np.array_equal(unique_values, np.array([1])):
        raise ValueError(
            f"Segmentation contains non-binary values: {unique_values}"
        )


def interactive_segmentation_viewer(
    original_image: Union[str, sitk.Image],
    segmentation_paths: List[str],
    consensus_mask: Optional[sitk.Image] = None,
    cmap: str = 'gray',
    mask_alpha: float = 0.3,
    base_width: int = 6  # Width per subplot
) -> None:
    """
    Create an interactive viewer for 3D segmentations with a slider for slice navigation.
    
    Args:
        original_image: Original image or path to image
        segmentation_paths: List of paths to segmentation masks
        consensus_mask: Optional STAPLE consensus mask
        cmap: Colormap for the original image
        mask_alpha: Transparency of segmentation overlay
        base_width: Width of each subplot in inches
    """
    # Calculate total number of plots and figure size
    n_plots = len(segmentation_paths) + 1  # original + segmentations
    if consensus_mask is not None:
        n_plots += 1  # add one for STAPLE consensus
    
    # Calculate figure size based on number of plots
    # Width is base_width per subplot, height is 2/3 of total width
    figsize = (base_width * n_plots, base_width * n_plots * 2/3)

def get_array_from_input(input_data):
    """Convert various input types to numpy array."""
    if input_data is None:
        return None
    
    # If it's already a numpy array
    if isinstance(input_data, np.ndarray):
        return input_data
    
    # If it's a SimpleITK image
    if isinstance(input_data, sitk.Image):
        return sitk.GetArrayFromImage(input_data)
    
    # If it's a string or Path
    if isinstance(input_data, (str, Path)):
        # Try SimpleITK first
        try:
            return sitk.GetArrayFromImage(sitk.ReadImage(str(input_data)))
        except:
            # If SimpleITK fails, try nibabel
            return nib.load(str(input_data)).get_fdata()
    
    # If it's a nibabel image
    if isinstance(input_data, nib.Nifti1Image):
        return input_data.get_fdata()
    
    raise TypeError(f"Unsupported input type: {type(input_data)}")

def interactive_segmentation_viewer(
    original_image: Union[str, sitk.Image],
    segmentation_paths: List[str],
    consensus_mask: Optional[sitk.Image] = None,
    cmap: str = 'gray',
    mask_alpha: float = 0.3,
    base_width: int = 3,  # Width per subplot
    raters: List[str] = None
) -> None:
    """
    Create an interactive viewer for 3D segmentations with a slider for slice navigation.
    Displays plots in 2 rows.
    """
    plt.ion()
    
    if isinstance(original_image, str):
        original_image = sitk.ReadImage(original_image)
    
    original_array = sitk.GetArrayFromImage(original_image)
    
    segmentations = []
    for seg_path in segmentation_paths:
        seg = sitk.ReadImage(seg_path)
        seg = convert_to_binary_mask(seg)
        seg_array = sitk.GetArrayFromImage(seg)
        segmentations.append(seg_array)

    n_plots = len(segmentations) + 1
    if consensus_mask is not None:
        n_plots += 1
        consensus_array = get_array_from_input(consensus_mask)
        if consensus_array.shape != original_array.shape:
            # Transpose if necessary
            consensus_array = np.transpose(consensus_array, (2, 1, 0))
        assert consensus_array.shape == original_array.shape, f"Consensus shape mismatch: {consensus_array.shape} vs {original_array.shape}"
    
    # Calculate rows and columns
    n_cols = (n_plots + 1) // 2  # Ceiling division to handle odd numbers
    n_rows = 2
    
    # Adjust figure size for 2 rows
    figsize = (base_width * n_cols, base_width * n_rows)
    fig = plt.figure(figsize=figsize)
    plt.subplots_adjust(bottom=0.2)
    
    # Create axes for images
    axes = []
    for i in range(n_plots):
        # Calculate row and column position
        row = i // n_cols
        col = i % n_cols
        ax = plt.subplot(n_rows, n_cols, i + 1)
        axes.append(ax)
    
    # Create slider axis
    slider_ax = plt.axes([0.1, 0.05, 0.8, 0.03])
    slider = Slider(
        ax=slider_ax,
        label='Slice',
        valmin=0,
        valmax=original_array.shape[0] - 1,
        valinit=original_array.shape[0] // 2,
        valstep=1
    )
    
    def update(val):
        slice_idx = int(slider.val)
        
        # Update original image
        axes[0].clear()
        axes[0].imshow(original_array[slice_idx], cmap=cmap)
        axes[0].axis('off')
        axes[0].set_title('Original')
        
        # Update segmentations
        for i, seg_array in enumerate(segmentations, 1):
            axes[i].clear()
            axes[i].imshow(original_array[slice_idx], cmap=cmap)
            mask = np.ma.masked_where(seg_array[slice_idx] == 0, seg_array[slice_idx])
            axes[i].imshow(mask, alpha=mask_alpha, cmap='autumn')
            axes[i].axis('off')
            if raters is not None:
                axes[i].set_title(f'Rater: {raters[i-1]}')
            else:
                axes[i].set_title(f'Rater {i}')
        
        # Update STAPLE consensus if provided
        if consensus_mask is not None:
            axes[-1].clear()
            axes[-1].imshow(original_array[slice_idx], cmap=cmap)
            consensus_mask_slice = np.ma.masked_where(
                consensus_array[slice_idx] == 0, 
                consensus_array[slice_idx]
            )
            axes[-1].imshow(consensus_mask_slice, alpha=mask_alpha, cmap='autumn')
            axes[-1].axis('off')
            axes[-1].set_title('STAPLE')
        
        fig.canvas.draw_idle()
    
    slider.on_changed(update)
    update(original_array.shape[0] // 2)
    
    def on_key(event):
        if event.key == 'up' or event.key == 'right':
            new_val = min(slider.val + 1, slider.valmax)
            slider.set_val(new_val)
        elif event.key == 'down' or event.key == 'left':
            new_val = max(slider.val - 1, slider.valmin)
            slider.set_val(new_val)
    
    fig.canvas.mpl_connect('key_press_event', on_key)
    plt.show()
    plt.ioff()

def convert_to_binary_mask(seg: sitk.Image) -> sitk.Image:
    """
    Convert a segmentation to a binary mask.
    
    Args:
        seg: Input segmentation image
    
    Returns:
        Binary mask with values 0 and 1
    """
    # Check if already binary
    if len(np.unique(sitk.GetArrayFromImage(seg))) > 2:
        # Put everything below 1.1 to 0 and everything above 1.1 to 1
        seg = sitk.BinaryThreshold(seg, 
                          lowerThreshold=1.1, 
                          upperThreshold=float('inf'),
                          insideValue=1,
                          outsideValue=0)
    
    # Ensure binary mask is of type UInt8
    return sitk.Cast(seg > 0, sitk.sitkUInt8)

def create_staple_consensus(
    original_image_path: str,
    segmentation_paths: List[str],
    output_path: str,
    confidence_threshold: float = 0.5,
    visualize: bool = False,
    plot_verification: bool = False,
    do_preprocessing: bool = True,
    do_adaptive_thresholding: bool = True,
    do_vessel_enhancement: bool = True
    
) -> sitk.Image:
    """
    Create and optionally visualize STAPLE consensus segmentation.
    """
    if len(segmentation_paths) < 2:
        raise ValueError("STAPLE requires at least 2 segmentations")
    
    # Read the original image
    try:
        original_image = sitk.ReadImage(original_image_path)
    except Exception as e:
        raise ValueError(f"Error reading original image {original_image_path}: {str(e)}")
    
   # Read all segmentation masks
    segmentations = []
    for seg_path in segmentation_paths:
        if not os.path.exists(seg_path):
            print(f"Segmentation file not found: {seg_path}")
            continue
        
        try:
            seg = sitk.ReadImage(seg_path)
            seg = convert_to_binary_mask(seg)
            verify_segmentation_values(seg)
            seg.CopyInformation(original_image)
            segmentations.append(seg)
        except Exception as e:
            raise ValueError(f"Error reading {seg_path}: {str(e)}")

    if segmentations == []:
        print("No valid segmentations found")
        return
    
    # Verify spatial consistency with original image
    verify_spatial_consistency(original_image, segmentations, plot_verification)

    # Apply STAPLE algorithm
    staple_filter = sitk.STAPLEImageFilter()
    staple_filter.SetForegroundValue(1)

    
    # IMPROVEMENTS --- Preprocess segmentations
    preprocessed_segs = [preprocess_segmentation(seg) for seg in segmentations] if do_preprocessing else segmentations

    if plot_verification:
        plot_img_multiple_seg(sitk.GetArrayFromImage(original_image),
                            [sitk.GetArrayFromImage(seg) for seg in preprocessed_segs])
    
    # Get STAPLE probability map
    consensus_prob = staple_filter.Execute(preprocessed_segs)
    plot_img_seg(sitk.GetArrayFromImage(original_image), sitk.GetArrayFromImage(consensus_prob))

    # IMPROVEMENTS --- Apply adaptive thresholding
    binary_consensus = adaptive_staple_threshold(consensus_prob, preprocessed_segs) if do_adaptive_thresholding else sitk.Cast(consensus_prob > confidence_threshold, sitk.sitkUInt8)

    # IMPROVEMENTS --- Analyze vessel characteristics and Enhance connectivity
    if do_vessel_enhancement:
        
        try:
            vessel_stats = analyze_vessel_characteristics(preprocessed_segs, original_image)
            # Use these parameters in enhancement
            binary_consensus = enhance_vessel_connectivity(
                binary_consensus, 
                original_image,
                vessel_radius_mm=vessel_stats['recommended_radius_mm'],
                min_vessel_length_mm=vessel_stats['recommended_min_length_mm']
            )
        except Exception as e:
            print(f"Error analyzing vessel characteristics: {str(e)}")
            print(f"It was not possible to enhance vessel connectivity for {output_path}")
            print("Saving the consensus segmentation without enhancement...")
            
        #print("\nVessel Analysis Results:")
        #print(f"Recommended vessel radius: {vessel_stats['recommended_radius_mm']:.2f} mm")
        #print(f"Recommended minimum length: {vessel_stats['recommended_min_length_mm']:.2f} mm")
        #print(f"Recommended minimum volume: {vessel_stats['recommended_min_volume_mm3']:.2f} mm³")
        
        
    # Preserve metadata from original image
    binary_consensus.CopyInformation(original_image)

    # Save the consensus segmentation
    try:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        sitk.WriteImage(binary_consensus, output_path)
    except Exception as e:
        raise IOError(f"Error saving consensus segmentation: {str(e)}")
    
    if visualize:
        interactive_segmentation_viewer(
            original_image,
            segmentation_paths,
            binary_consensus,
            mask_alpha=0.9,
            base_width=3
        )
    
    return binary_consensus


