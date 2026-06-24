interface AvatarImageProps {
  src: string;
  size: number;
  className?: string;
  style?: React.CSSProperties;
  wrapperClassName?: string;
  wrapperStyle?: React.CSSProperties;
}

export function AvatarImage({
  src,
  size,
  className = '',
  style,
  wrapperClassName,
  wrapperStyle,
}: AvatarImageProps) {
  const width = size;
  const height = Math.round(size * 1.4);
  const borderRadius = '4px';

  const imgEl = (
    <img
      src={src}
      alt=""
      className={className}
      style={{
        width,
        height,
        borderRadius,
        objectFit: 'cover',
        ...style,
      }}
    />
  );

  if (wrapperClassName || wrapperStyle) {
    return (
      <div
        className={wrapperClassName}
        style={{ borderRadius, ...wrapperStyle }}
      >
        {imgEl}
      </div>
    );
  }

  return imgEl;
}
