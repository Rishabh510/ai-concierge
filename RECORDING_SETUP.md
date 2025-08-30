# Audio Recording Setup Guide

This guide explains how to set up audio recording for all participants in your LiveKit room and automatically upload recordings to Amazon S3.

## Overview

The recording service captures audio from all participants in the LiveKit room and uploads the recordings to your S3 bucket. This is useful for:
- Call quality monitoring
- Compliance and legal requirements
- Training and improvement purposes
- Analytics and insights

## Configuration

### Environment Variables

Add the following environment variables to your `.env.local` file:

```bash
# Audio Recording Configuration
ENABLE_AUDIO_RECORDING=true
S3_RECORDING_BUCKET=your-s3-bucket-name
S3_RECORDING_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
RECORDING_FILE_FORMAT=ogg
RECORDING_AUDIO_ONLY=true
```

### Configuration Options

| Variable | Description | Default | Options |
|----------|-------------|---------|---------|
| `ENABLE_AUDIO_RECORDING` | Enable/disable recording | `false` | `true`/`false` |
| `S3_RECORDING_BUCKET` | S3 bucket name for recordings | - | Your bucket name |
| `S3_RECORDING_REGION` | AWS region for S3 bucket | `us-east-1` | AWS region |
| `AWS_ACCESS_KEY_ID` | AWS access key | - | Your AWS access key |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | - | Your AWS secret key |
| `RECORDING_FILE_FORMAT` | Audio file format | `ogg` | `ogg`, `mp4`, `webm` |
| `RECORDING_AUDIO_ONLY` | Record audio only | `true` | `true`/`false` |

## AWS S3 Setup

### 1. Create S3 Bucket

1. Go to AWS S3 Console
2. Create a new bucket with a unique name
3. Choose your preferred region
4. Configure bucket settings (recommended: enable versioning for backup)

### 2. Configure Bucket Permissions

Create an IAM policy for the recording service:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::your-bucket-name",
                "arn:aws:s3:::your-bucket-name/*"
            ]
        }
    ]
}
```

### 3. Create IAM User

1. Create a new IAM user for the recording service
2. Attach the policy created above
3. Generate access keys for the user
4. Use these keys in your environment variables

## File Structure

Recordings are stored in S3 with the following structure:

```
s3://your-bucket-name/
└── recordings/
    ├── room-name_20241201_143022.ogg
    ├── room-name_20241201_143156.ogg
    └── ...
```

### File Naming Convention

- Format: `{room_name}_{timestamp}.{format}`
- Example: `room-abc123_20241201_143022.ogg`
- Timestamp format: `YYYYMMDD_HHMMSS`

## How It Works

1. **Recording Start**: When a LiveKit room session begins, the recording service automatically starts capturing audio from all participants
2. **Real-time Upload**: Audio is streamed to S3 as it's recorded
3. **Recording Stop**: When the session ends, the recording is finalized and uploaded to S3
4. **Error Handling**: If recording fails, the session continues without recording

## Monitoring

### Logs

The recording service logs important events:

```
INFO - Audio recording service initialized successfully
INFO - Recording started successfully with egress ID: egress_abc123
INFO - Recording will be saved to S3: s3://your-bucket/recordings/room-abc123_20241201_143022.ogg
INFO - Recording stopped successfully
```

### Recording Status

You can check recording status programmatically:

```python
status = await recording_service.get_recording_status(ctx)
if status:
    print(f"Status: {status['status']}")
    print(f"Started: {status['started_at']}")
    print(f"Ended: {status['ended_at']}")
```

## Troubleshooting

### Common Issues

1. **Recording not starting**
   - Check if `ENABLE_AUDIO_RECORDING=true`
   - Verify AWS credentials are correct
   - Ensure S3 bucket exists and is accessible

2. **S3 upload failures**
   - Check AWS credentials and permissions
   - Verify bucket name and region
   - Check network connectivity

3. **Recording stops unexpectedly**
   - Check LiveKit egress service status
   - Verify room connection stability
   - Check for any errors in logs

### Debug Mode

Enable debug logging to see detailed recording information:

```python
import logging
logging.getLogger("recording_service").setLevel(logging.DEBUG)
```

## Security Considerations

1. **Access Control**: Ensure only authorized users can access recordings
2. **Encryption**: Consider enabling S3 server-side encryption
3. **Retention**: Implement a retention policy for recordings
4. **Compliance**: Ensure recordings comply with relevant regulations (GDPR, HIPAA, etc.)

## Performance Notes

- Recording adds minimal overhead to the LiveKit session
- Audio files are compressed to minimize storage costs
- S3 uploads happen in real-time to avoid data loss
- Recording service gracefully handles failures without affecting the main session

## Integration with Existing Code

The recording service is automatically integrated into both entrypoints:
- `entrypoint()` - For telephony calls
- `entrypoint_webtest()` - For web-based testing

No additional code changes are required once configuration is set up.
