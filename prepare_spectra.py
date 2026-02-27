import os, shutil

template_path = "/zeus1/isgri_local/template/"


def prepare_spectra_files(workdir, source):
    """
    Prepares the directories and files for the spectra extraction on the cluster.
    Args:
        workdir (str): The working directory where the spectra files will be created.
        source (str): The source name.
        with_saturation (bool): If True, prepares spectra for saturated bursts.
    """

    if os.path.exists(workdir):
        raise ValueError("Workdir already exists")
    os.makedirs(workdir)
    os.makedirs(os.path.join(workdir, "spectra"))
    os.makedirs(os.path.join(workdir, "logs"))
    os.makedirs(os.path.join(workdir, "logs", "output"))
    os.makedirs(os.path.join(workdir, "logs", "errors"))
    with open(os.path.join(workdir, "exec.sh"), "w") as f:
        print(r"#!/bin/sh", file=f)
        print(r'DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )" ', file=f)
        print(r'sed -i "s|ABSPATH|$DIR|g" "job.sh"', file=f)
        print(r'sed -i "s|ABSPATH|$DIR|g" "data.txt"', file=f)
        print(rf"qsub -N {source} job.sh", file=f)


def edit_spectra_template(template, source, maxno, emin, emax, bins, osa_workpath):
    template_keys = {
        "TEMPLATE_MAXNO": maxno,
        "TEMPLATE_SOURCE": source,
        "TEMPLATE_EMIN": emin,
        "TEMPLATE_EMAX": emax,
        "TEMPLATE_BINS": bins,
        "TEMPLATE_OSA_RBP": osa_workpath,
    }
    for key in template_keys:
        template = template.replace(key, str(template_keys[key]))
    return template


def prepare_spectra(
    source,
    data,
    workdir,
    osa_workpath,
    emin=20,
    emax=300,
    bins=-12,
):
    """
    Prepares the spectra files for the given data and source.
    Args:
        data (astropy table): The data to be used for preparing the spectra. Required columns are:
            - "rev": The revolution number.
            - "scw": The scw number.
            - "Saturation": A boolean indicating if the burst is saturated -- only needed if with_saturation is True.
            - "UID": The unique identifier for the burst.
            - "BB_tstart": The start time of the burst in seconds.
            - "BB_tstop": The stop time of the burst in seconds.
        source (str): The source name.
        workdir (str): The working directory where the spectra files will be created.
        margins (tuple): The margins to be added to the start and stop times of the bursts.
    """
    print("Preparing spectra files...")
    print("Workdir:", workdir)
    print("Source:", source)
    print("Emin:", emin, "Emax:", emax, "Bins:", bins)
    if not os.path.exists(data):
        raise ValueError("Data file does not exist")
    shutil.copy(data, os.path.join(workdir, "data.txt"))
    with open(os.path.join(workdir, "data.txt")) as f:
        lines = f.readlines()

    prepare_spectra_files(workdir, source)

    with open(template_path + "bursts_spectrum.sh") as f:
        template = f.read()
    template = edit_spectra_template(template, source, len(lines), emin, emax, bins, osa_workpath)
    with open(os.path.join(workdir, "job.sh"), "w") as f:
        f.write(template)
