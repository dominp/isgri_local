import os, shutil
from numpy import array_split
from astropy.io import fits
from itertools import cycle

template_path = "/zeus1/isgri_local/template/"


def prepare_specat(name, ra, dec, outpath, inpath=None):
    """Generate specat file for the given source. The specat file is a FITS file that contains the source information, in a format readable by the OSA.

    Parameters
    ----------
    name : str
        The name of the source.
    ra : float
        The right ascension of the source in degrees.
    dec : float
        The declination of the source in degrees.
    inpath : str
        The path to the input specat template file.  Default is the specat template file provided in the template directory.
    outpath : str
        The path to the output specat file.
    """
    if inpath is None:
        inpath = os.path.join(template_path, "specat.fits")
    with fits.open(inpath) as f:
        d = f[1].data
        d["SOURCE_ID"][0] = name
        d["NAME"][0] = name
        d["RA_OBJ"][0] = ra
        d["RA_FIN"][0] = ra
        d["DEC_OBJ"][0] = dec
        d["DEC_FIN"][0] = dec
        f.writeto(outpath, overwrite=True)


def create_scw_file(path, name, scws, maxno=5000):
    """Split a list of science windows into text files.

    Parameters
    ----------
    path : str
        Directory where the scw files will be written.
    name : str
        Base name prefix for the output files.
    scws : list
        List of science window IDs.
    maxno : int, optional
        Maximum number of ScWs per file. Default is 5000.

    Returns
    -------
    noscws : int
        Number of ScWs in the first (largest) chunk.
    file_names : list of str
        List of generated file names (basenames only).
    """
    noscws = len(scws)
    if noscws > maxno:
        no_arrays = len(scws) // maxno + 1
        scws = array_split(scws, no_arrays)
        noscws = len(scws[0])
    else:
        scws = [scws]
    file_names = []
    for i, scws_arr in enumerate(scws):
        scw_file = os.path.join(path, f"{name}{i}.txt")
        file_names.append(os.path.basename(scw_file))
        with open(scw_file, "w") as f:
            for scw in scws_arr:
                if type(scw) != str:
                    scw = scw.decode("UTF-8")
                print(scw, file=f)
    return noscws, file_names


def prepare_masks(
    name,
    scws,
    workdir,
    osa_workpath,
    specat_path=None,
    ra=None,
    dec=None,
    nodes=None,
    output_path=None,
    findgrb=True,
    emin=15,
    emax=300,
    location="werewolf",
    max_scws=5000,
):
    """Prepare PBS job scripts for ISGRI mask creation.

    Creates a working directory structure with specat, scw lists, and
    PBS job scripts ready to be submitted via the generated exec.sh.
    Optionally also prepares FindGRB jobs.

    Parameters
    ----------
    name : str
        Source name. Spaces are replaced with underscores.
    scws : list
        List of science window IDs.
    workdir : str
        Base working directory. A 'Mask' subdirectory will be created inside.
    osa_workpath : str
        OSA working path used as REP_BASE_PROD in the job scripts.
    specat_path : str, optional
        Path to an existing specat FITS file. If None, ra and dec must be provided.
    ra : float, optional
        Right ascension in degrees. Required if specat_path is None.
    dec : float, optional
        Declination in degrees. Required if specat_path is None.
    nodes : list of str, optional
        Compute nodes to cycle through. Default is ['4', '5'].
    output_path : str, optional
        Output path for results. Default is /storage/dominik/SRCS/<name>/.
    findgrb : bool, optional
        Whether to also prepare FindGRB jobs. Default is True.
    emin : int, optional
        Minimum energy in keV. Default is 15.
    emax : int, optional
        Maximum energy in keV. Default is 300.
    location : str, optional
        Template location prefix (e.g. 'werewolf'). Default is 'werewolf'.
    """
    workdir = os.path.join(workdir, "Mask")
    if os.path.exists(workdir):
        raise ValueError(f"{workdir} already exists")

    name = name.strip().replace(" ", "_")
    os.makedirs(workdir)
    os.makedirs(os.path.join(workdir, "scw"))
    os.makedirs(os.path.join(workdir, "exec"))
    os.makedirs(os.path.join(workdir, "specat"))
    os.makedirs(os.path.join(workdir, "log"))
    os.makedirs(os.path.join(workdir, "log", "output"))
    os.makedirs(os.path.join(workdir, "log", "error"))

    if specat_path:
        specat_name = os.path.basename(specat_path)
        shutil.copy(specat_path, os.path.join(workdir, "specat", specat_name))
    elif not ra or not dec:
        raise ValueError("RA and DEC must be provided if specat_path is not provided")
    else:
        specat_name = name + ".fits"
        prepare_specat(
            name,
            ra,
            dec,
            os.path.join(workdir, "specat", specat_name),
            os.path.join(template_path, "specat.fits"),
        )

    scw_name = name + "_"
    no_scws, scw_lists = create_scw_file(os.path.join(workdir, "scw"), scw_name, scws, maxno=max_scws)

    if nodes is None:
        nodes = ["4", "5"]

    if output_path is None:
        output_path = os.path.join("/storage/dominik/SRCS/", name + "/")
    else:
        output_path = os.path.join(output_path, name + "/")
    selected_template = template_path + f"{location}_mask_creation.sh"
    if not os.path.exists(selected_template):
        raise ValueError(f"Template {selected_template} does not exist")
    with open(selected_template) as f:
        template = f.read()
    template_keys = {
        "TEMPLATE_MAXNO": no_scws,
        "TEMPLATE_SPECAT": specat_name,
        "TEMPLATE_OUTPUT": output_path,
        "TEMPLATE_OSA_RBP": osa_workpath,
    }
    for key in template_keys:
        template = template.replace(key, str(template_keys[key]))
    exec_files = []
    for ids, (scw_list, node) in enumerate(zip(scw_lists, cycle(nodes))):
        exec_files.append(file := f"job_{ids}.sh")
        with open(os.path.join(workdir, "exec", file), "w") as f:
            f.write(template.replace("TEMPLATE_SCW", scw_list).replace("TEMPLATE_NODE", node))

    with open(os.path.join(workdir, "exec.sh"), "w") as f:
        print(r"#!/bin/sh", file=f)
        print(rf'mkdir -p "{output_path}"', file=f)
        print(r'DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )" ', file=f)
        for idf, file in enumerate(exec_files):
            print(rf'sed -i "s|ABSPATH|$DIR|g" "exec/{file}"', file=f)
            print(rf"qsub -N {name}_{idf} exec/{file}", file=f)

    if findgrb:
        workdir = workdir[:-4]
        prepare_findgrb(name, scws, workdir, emin=emin, emax=emax)


def prepare_findgrb(name, scws, workdir, archive_path=None, mask_path=None, emin=15, emax=300):
    """Prepare PBS job scripts for FindGRB analysis.

    Parameters
    ----------
    name : str
        Source name.
    scws : list
        List of science window IDs.
    workdir : str
        Base working directory. A 'FindGRB' subdirectory will be created inside.
    archive_path : str, optional
        Path to the ScW archive. Default is /anita/archivio/scw/.
    mask_path : str, optional
        Path to the ISGRI mask files. Default is /zeus1/SRCS/<name>/.
    emin : int, optional
        Minimum energy in keV. Default is 15.
    emax : int, optional
        Maximum energy in keV. Default is 300.
    """
    workdir = os.path.join(workdir, "FindGRB")
    if os.path.exists(workdir):
        raise ValueError(f"{workdir} already exists")
    if archive_path is None:
        archive_path = "/anita/archivio/scw/"
    if mask_path is None:
        mask_path = f"/zeus1/SRCS/{name}/"
    os.makedirs(workdir)
    os.makedirs(os.path.join(workdir, "scw"))
    os.makedirs(os.path.join(workdir, "exec"))
    os.makedirs(os.path.join(workdir, "log"))
    os.makedirs(os.path.join(workdir, "output"))

    scw_name = name + "_"
    _, scw_lists = create_scw_file(os.path.join(workdir, "scw"), scw_name, scws, maxno=999999)
    shutil.copy(os.path.join(template_path, "run_findgrb.sh"), os.path.join(workdir, "exec", "run.sh"))
    shutil.copy(os.path.join(template_path, "exec_findgrb.sh"), os.path.join(workdir, "exec.sh"))
    with open(os.path.join(template_path, "findgrb.pro")) as f:
        template = f.read()
    template_keys = {
        "TEMPLATE_ARCHIVE": archive_path,
        "TEMPLATE_MASK": mask_path,
        "TEMPLATE_EMIN": emin,
        "TEMPLATE_EMAX": emax,
    }
    for key in template_keys:
        template = template.replace(key, str(template_keys[key]))
    for scw_list in scw_lists:
        exec_file = scw_list.split(".")[0] + ".pro"
        output_name = f"{scw_list.split('.')[0]}_{emin}_{emax}"
        with open(os.path.join(workdir, "exec", exec_file), "w") as f:
            f.write(template.replace("TEMPLATE_SCW", scw_list).replace("TEMPLATE_OUTPUT", output_name))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Prepare mask and FindGRB jobs for ISGRI analysis.")
    parser.add_argument("name", type=str, help="Source name")
    parser.add_argument("scws", type=str, help="Path to a text file containing science window IDs (one per line)")
    parser.add_argument("workdir", type=str, help="Working directory where output folders will be created")
    parser.add_argument("osa_workpath", type=str, help="OSA working path (REP_BASE_PROD)")

    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument("--radec", nargs=2, type=float, metavar=("RA", "DEC"), help="RA and DEC in degrees")
    source_group.add_argument("--specat", type=str, default=None, help="Path to an existing specat FITS file")

    parser.add_argument(
        "--output-path",
        type=str,
        default=None,
        help="Output path for results (default: /storage/dominik/SRCS/<name>/)",
    )
    parser.add_argument("--nodes", type=str, nargs="+", default=None, help="List of compute nodes (default: 4 5)")
    parser.add_argument("--no-findgrb", action="store_true", help="Skip FindGRB preparation")
    parser.add_argument("--emin", type=int, default=15, help="Minimum energy in keV (default: 15)")
    parser.add_argument("--emax", type=int, default=300, help="Maximum energy in keV (default: 300)")
    parser.add_argument(
        "--location", type=str, default="werewolf", help="Location for mask creation template (default: werewolf)"
    )
    parser.add_argument(
        "--max-scws", type=int, default=5000, help="Maximum number of ScWs per job script (default: 5000)"
    )

    args = parser.parse_args()

    with open(args.scws) as f:
        scws = [line.strip() for line in f if line.strip()]

    ra, dec = args.radec if args.radec else (None, None)

    prepare_masks(
        name=args.name,
        scws=scws,
        workdir=args.workdir,
        osa_workpath=args.osa_workpath,
        specat_path=args.specat,
        ra=ra,
        dec=dec,
        nodes=args.nodes,
        output_path=args.output_path,
        findgrb=not args.no_findgrb,
        emin=args.emin,
        emax=args.emax,
        location=args.location,
        max_scws=args.max_scws,
    )
