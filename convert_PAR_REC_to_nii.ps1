# Define paths
$sourceDir = "D:\NESDA\W3\par_rec_AmsLei"
$dcm2niixPath = "D:\software\dcm2niix\dcm2niix.exe"
                 
# Process each subject
Get-ChildItem -Path $sourceDir -Directory | ForEach-Object {
    $subjectDir = $_.FullName
    $subjectId = $_.Name
    
    # Process each session
    Get-ChildItem -Path $subjectDir -Directory | ForEach-Object {
        $sessionDir = $_.FullName
        $sessionId = $_.Name
        
        # Process anatomical data
        $anatDir = Join-Path -Path $sessionDir -ChildPath "anat"
        if (Test-Path $anatDir) {
            Write-Host "Converting anat data for $subjectId/$sessionId"
            & $dcm2niixPath -b y -z y -f "${subjectId}_${sessionId}_T1w" -o $anatDir $anatDir
        }
        
        # Process functional data
        $funcDir = Join-Path -Path $sessionDir -ChildPath "func"
        if (Test-Path $funcDir) {
            Write-Host "Converting func data for $subjectId/$sessionId"
            & $dcm2niixPath -b y -z y -f "${subjectId}_${sessionId}_task-rest_bold" -o $funcDir $funcDir
        }
    }
}

Write-Host "Conversion complete!"