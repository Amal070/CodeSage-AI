import { Icon } from './Icon';

export default function Button({
  children,
  type = 'button',
  variant = 'primary', // 'primary' | 'secondary' | 'ghost' | 'danger' | 'success'
  size = 'md', // 'sm' | 'md' | 'lg'
  loading = false,
  loadingText = null,
  disabled = false,
  icon = null,
  iconPosition = 'left',
  className = '',
  onClick,
  ...props
}) {
  const isDisabled = disabled || loading;

  const getVariantClass = () => {
    switch (variant) {
      case 'secondary':
        return 'btn-secondary';
      case 'ghost':
        return 'btn-ghost';
      case 'danger':
        return 'btn-danger';
      case 'success':
        return 'btn-success';
      case 'primary':
      default:
        return 'btn-primary';
    }
  };

  const getSizeClass = () => {
    switch (size) {
      case 'sm':
        return 'btn-sm';
      case 'lg':
        return 'btn-lg';
      default:
        return '';
    }
  };

  const buttonClasses = `btn ${getVariantClass()} ${getSizeClass()} ${loading ? 'btn-loading' : ''} ${className}`.trim();

  return (
    <button
      type={type}
      className={buttonClasses}
      disabled={isDisabled}
      onClick={isDisabled ? undefined : onClick}
      aria-busy={loading}
      {...props}
    >
      {loading ? (
        <>
          <Icon name="spinner" size={size === 'sm' ? 14 : 16} className="btn-spinner" />
          <span>{loadingText || children}</span>
        </>
      ) : (
        <>
          {icon && iconPosition === 'left' && (
            typeof icon === 'string' ? <Icon name={icon} size={size === 'sm' ? 14 : 16} /> : icon
          )}
          <span>{children}</span>
          {icon && iconPosition === 'right' && (
            typeof icon === 'string' ? <Icon name={icon} size={size === 'sm' ? 14 : 16} /> : icon
          )}
        </>
      )}
    </button>
  );
}
