import pytest
import knightswhosaydb
from knightswhosaydb import mosaic

@pytest.mark.skip(reason="Hardcoded local directory D:/GitHub/... Needs dynamic pathing for GitHub Actions.")

@pytest.mark.parametrize("frequency", [200, 400])
@pytest.mark.parametrize("file_type", ['fmgt', 'kmall'])
@pytest.mark.parametrize("res", [1, 2])
@pytest.mark.parametrize("template_path", [None, 'D:/GIS/scratch/back_1m_mean.tif'])
@pytest.mark.parametrize("apply_avg", [True, False])
@pytest.mark.parametrize("layer", ['backscatter', 'depth'])
def test_mosaic_parameter_grid(tmp_path, frequency, file_type, res, template_path, apply_avg, layer):

    dir = "D:/GitHub/knightswhosaydb/test_data"

    try:
        mosaic(
            dir_path=dir,
            format=file_type,
            layer=layer,
            out_lines=tmp_path / "scratch_lines",
            mosaic_path=tmp_path / f"mosaic_{frequency}khz_{layer}_{res}_{apply_avg}.tif",
            frequency=frequency,
            crs='EPSG:32622',
            template_path=template_path,
            apply_avg=apply_avg,
            res=res
        )
    except Exception as e:
        pytest.fail(f"Mosaic crashed with {file_type}, {frequency}khz ,{layer}, res={res}, apply_avg={apply_avg}. Error: {e}")

    output_tifs = list(tmp_path.glob("*.tif"))
    assert len(output_tifs) > 0, "No TIF files were generated!"