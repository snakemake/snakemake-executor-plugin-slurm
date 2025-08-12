import shlex
from datetime import datetime, timedelta



def query_job_status_sacct(jobuid, timeout: int = 30) -> Dict[str, JobStatus]:
    """
    Query job status using sacct command
    
    Args:
        job_ids: List of SLURM job IDs
        timeout: Timeout in seconds for subprocess call
        
    Returns:
        Dictionary mapping job ID to JobStatus object
    """
    if not jobuid:
        return {}
    
    # We use this sacct syntax for argument 'starttime' to keep it compatible
    # with slurm < 20.11
    sacct_starttime = f"{datetime.now() - timedelta(days=2):%Y-%m-%dT%H:00}"
    # previously we had
    # f"--starttime now-2days --endtime now --name {self.run_uuid}"
    # in line 218 - once v20.11 is definitively not in use any more,
    # the more readable version ought to be re-adapted

    try:
        # -X: only show main job, no substeps
        query_command = f"""sacct -X --parsable2 \
                        --clusters all \
                        --noheader --format=JobIdRaw,State \
                        --starttime {sacct_starttime} \
                        --endtime now --name {self.run_uuid}"""
        
        # for better redability in verbose output
        query_command = " ".join(shlex.split(query_command))

        return query_command 

def query_job_status_squeue(job_ids: List[str], timeout: int = 30) -> Dict[str, JobStatus]:
    """
    Query job status using squeue command (newer SLURM functionality)
    
    Args:
        job_ids: List of SLURM job IDs
        timeout: Timeout in seconds for subprocess call
        
    Returns:
        Dictionary mapping job ID to JobStatus object
    """
    if not job_ids:
        return {}
    
    try:
        # Build squeue command
        query_command = """
            squeue \
            --format=%i|%T \  
            --states=all \
            --noheader \
            --name {self.run_uuid}
            """
        query_command = shlex.split(query_command)

        return query_command