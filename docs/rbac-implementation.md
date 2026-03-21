# Role-Based Access Control (RBAC) Implementation

## Overview

The Probation Management System now has comprehensive role-based access control (RBAC) implemented across all major modules. This document outlines the permission structure, implementation details, and usage guidelines.

## User Roles

The system supports five distinct user roles:

### 1. **Administrator (Admin)**
- **Access Level:** Full system access
- **Capabilities:**
  - View all offenders and cases (unscoped)
  - Create/edit/delete offenders
  - Create/edit/delete cases and assign officers
  - Manage all users (create, edit, delete, view)
  - Manage system configuration
  - View all check-ins and monitoring data
  - Create/edit/delete programs and categories
  - View all reports and analytics
  - Perform system-wide analytics

**Key Implementation:**
- Use `@admin_required` decorator on views
- Or use `AdminRequiredMixin` in class-based views
- Check: `if request.user.role == User.Role.ADMIN`

### 2. **Probation Officer**
- **Access Level:** Can manage assigned offenders and their cases
- **Capabilities:**
  - View only offenders assigned to them
  - Create new offenders (will be in their caseload)
  - Edit/update their assigned offenders
  - Cannot delete offenders
  - Manage check-ins for their assigned offenders
  - Create risk assessments for their cases
  - View/manage programs for their assigned offenders
  - Cannot access admin functions
  - Cannot manage other users

**Key Scoping:**
- Officers only see cases where `Case.assigned_officer == request.user`
- Officers only see offenders in their caseload
- Officers only see check-ins for their assigned offenders

**Implementation:**
- Use `@officer_required` decorator
- Or use `OfficerRequiredMixin` in class-based views
- Use `user_can_view_offender()` helper to verify access
- Use `user_can_edit_offender()` helper for edit operations

### 3. **Offender**
- **Access Level:** View-only access to their own data
- **Capabilities:**
  - View their own profile
  - View their own assigned case information
  - View their own check-in history
  - View their own program enrollments and progress
  - Edit their own profile (limited fields only)
  - Cannot view other offenders' information
  - Cannot access officer or admin functions

**Key Scoping:**
- Offenders can only see data where the offender = their user record
- Limited to their own case, check-ins, and programs
- Profile edits restricted to non-sensitive fields

**Implementation:**
- Use `@offender_required` decorator
- Check: `if request.user.role == User.Role.OFFENDER`
- Use `user_can_view_offender()` to check self-access

### 4. **Judiciary Staff**
- **Access Level:** View-only limited access
- **Capabilities:**
  - View offender information (scoped by institution if implemented)
  - View case details and compliance status
  - View risk assessments and reports
  - Cannot modify any data
  - Cannot create offenders or cases
  - Cannot manage users

**Implementation:**
- Use `@judiciary_or_admin_required` decorator
- Add institution-level scoping filters in production

### 5. **NGO Staff**
- **Access Level:** Program-focused limited access
- **Capabilities:**
  - View and facilitate program enrollment
  - Create/manage programs they facilitate
  - View offenders enrolled in their programs
  - Cannot view all offenders
  - Cannot access monitoring or case data (limited)
  - Cannot manage users

**Implementation:**
- Use `@ngo_or_admin_required` decorator
- Add program-specific scoping filters

## Implementation Files

### 1. **accounts/permissions.py** (New)
Central location for all RBAC logic:

```python
# Decorators for function-based views
@admin_required
@officer_required
@offender_required
@officer_or_admin_required
@ngo_or_admin_required
@judiciary_or_admin_required

# Mixins for class-based views
AdminRequiredMixin
OfficerRequiredMixin
OffenderRequiredMixin
OfficerOrAdminMixin
NGOOrAdminMixin
JudiciaryOrAdminMixin

# Helper functions for permission checks
user_can_view_offender(user, offender)
user_can_view_case(user, case)
user_can_view_checkin(user, checkin)
user_can_edit_offender(user, offender)
user_can_delete_offender(user, offender)
user_can_manage_users(user)
user_can_create_program_enrollment(user)
user_can_manage_programs(user)
user_can_view_reports(user)
user_can_create_assessment(user)

# Context processor
add_role_permissions(request)
```

### 2. **Updated Views**

#### accounts/views.py
- `login_view()`: Allow any unauthenticated user
- `dashboard_view()`: Render role-specific dashboard
- `profile_view()`: Updated to allow user self-edits
- `users_list_view()`: Admin only
- `create_user_view()`: Admin only
- `user_detail_view()`: Admin only
- `officers_list_view()`: Admin only

#### offenders/views.py
- `offender_list()`: Role-aware filtering
  - Admin: all offenders
  - Officer: their assigned offenders
  - Offender: their own record
  - Judiciary/NGO: all offenders (view-only)
- `offender_detail()`: Uses `user_can_view_offender()`
- `offender_create()`: Admin/Officer only
- `offender_update()`: Uses `user_can_edit_offender()`
- `offender_delete()`: Admin only

#### monitoring/views.py
- `CheckInListView`: Role-aware filtering
  - Admin: all check-ins
  - Officer: their own check-ins
  - Offender: their own check-ins
- `CheckInDetailView`: Uses `user_can_view_checkin()`
- `CheckInTypeCreateView`: Admin only
- `CheckInTypeUpdateView`: Admin only
- `CheckInTypeDeleteView`: Admin only

#### programs/views.py
- `ProgramCategoryListView`: Admin/Officer/NGO can access
- `ProgramCategoryCreateView`: Admin only
- `ProgramCategoryUpdateView`: Admin only
- `ProgramCategoryDeleteView`: Admin only
- `ProgramListView`: All authenticated users
- `EnrollmentCreateView`: Admin/Officer/NGO can create

## Settings Configuration

### settings.py
Added context processor to make role information available in all templates:

```python
TEMPLATES = [
    {
        'OPTIONS': {
            'context_processors': [
                # ... existing processors ...
                'accounts.permissions.add_role_permissions',
            ],
        },
    },
]
```

This adds the following to template context:
- `user_role`: User's role string
- `is_admin`: Boolean flag
- `is_officer`: Boolean flag
- `is_offender`: Boolean flag
- `is_judiciary`: Boolean flag
- `is_ngo`: Boolean flag

## Usage Examples

### Function-Based Views

```python
from accounts.permissions import officer_or_admin_required, user_can_view_offender

@officer_or_admin_required
def offender_list(request):
    # Only officers and admins can access
    offenders = Offender.objects.all()
    return render(request, 'offenders/list.html', {'offenders': offenders})

@login_required
def offender_detail(request, pk):
    offender = get_object_or_404(Offender, pk=pk)
    
    # Check if user can view this specific offender
    if not user_can_view_offender(request.user, offender):
        messages.error(request, 'Permission denied.')
        return redirect('offenders:list')
    
    return render(request, 'offenders/detail.html', {'offender': offender})
```

### Class-Based Views

```python
from accounts.permissions import OfficerOrAdminMixin
from django.views.generic import ListView

class OffenderListView(OfficerOrAdminMixin, ListView):
    model = Offender
    template_name = 'offenders/list.html'
    
    def get_queryset(self):
        if self.request.user.role == User.Role.ADMIN:
            return Offender.objects.all()
        else:
            # Officer: only their assigned offenders
            return Offender.objects.filter(
                cases__assigned_officer=self.request.user,
                cases__status='active'
            )
```

### Templates

Use role flags in templates to show/hide UI elements:

```html
{% if is_admin %}
    <a href="{% url 'admin:users_list' %}">Manage Users</a>
{% endif %}

{% if is_officer or is_admin %}
    <a href="{% url 'offenders:create' %}">Create Offender</a>
{% endif %}

{% if is_offender %}
    <p>Your assigned officer: {{ offender.active_case.assigned_officer.get_full_name }}</p>
{% endif %}

<!-- Only show edit button if user has permission -->
{% if can_edit %}
    <a href="{% url 'offenders:edit' offender.pk %}">Edit</a>
{% endif %}
```

## Permission Decision Matrix

| Action | Admin | Officer | Offender | Judiciary | NGO |
|--------|-------|---------|----------|-----------|-----|
| View all offenders | ✓ | ✗* | ✗ | ✓ | ✓ |
| View assigned offenders | ✓ | ✓ | ✗ | ✗ | ✗ |
| View own offender | ✓ | ✗ | ✓ | ✗ | ✗ |
| Create offender | ✓ | ✓ | ✗ | ✗ | ✗ |
| Edit offender | ✓ | ✓* | ✓** | ✗ | ✗ |
| Delete offender | ✓ | ✗ | ✗ | ✗ | ✗ |
| Manage users | ✓ | ✗ | ✗ | ✗ | ✗ |
| View check-ins | ✓ | ✓* | ✓** | ✓ | ✓ |
| Create check-in | ✓ | ✓* | ✗ | ✗ | ✗ |
| Manage programs | ✓ | ✓* | ✗ | ✗ | ✓ |
| View reports | ✓ | ✓ | ✓** | ✓ | ✓ |

**Legend:**
- ✓ = Full access
- ✓* = Scoped access (only assigned items)
- ✓** = View only (own data)
- ✗ = No access

## Security Best Practices Implemented

1. **Front-line Permission Checks**: Every view checks permissions immediately
2. **Scoped Queries**: Officers and offenders see filtered data
3. **Template-level Controls**: UI elements hidden based on permissions
4. **Multiple Permission Checks**: Both view-level and helper function checks
5. **Audit Trail**: All modifications can be traced by role
6. **Least Privilege**: Each role has minimum necessary permissions

## Testing RBAC

### Manual Testing Checklist

1. **Admin Login:**
   - [ ] Can access all admin pages
   - [ ] Can view all users
   - [ ] Can create/edit/delete users
   - [ ] Can view all offenders
   - [ ] Can create/edit/delete offenders
   - [ ] Can view all check-ins
   - [ ] Can manage programs

2. **Officer Login:**
   - [ ] Can view only their assigned offenders
   - [ ] Can create new offenders (auto-assigned to them)
   - [ ] Can view only their check-ins
   - [ ] Can create check-ins for assigned offenders
   - [ ] Cannot access user management
   - [ ] Cannot view other officers' data

3. **Offender Login:**
   - [ ] Can view only their own profile
   - [ ] Can see their assigned officer
   - [ ] Can view their check-in history
   - [ ] Can view their program enrollments
   - [ ] Cannot view other offenders
   - [ ] Cannot create offenders

4. **Judiciary Login:**
   - [ ] Can view all offenders (view-only)
   - [ ] Can view cases and reports
   - [ ] Cannot create/edit/delete records
   - [ ] Cannot manage users

5. **NGO Login:**
   - [ ] Can view program data
   - [ ] Can manage enrolled offenders
   - [ ] Cannot access case management
   - [ ] Cannot manage users

## Future Enhancements

1. **Institution-Level Scoping**: Filter data by institution/office
2. **Fine-Grained Permissions**: Add more specific permission granularity
3. **Audit Logging**: Log all permission checks and denied access attempts
4. **Time-Based Access**: Restrict access during certain hours
5. **IP Whitelisting**: Add IP-based access controls for certain roles
6. **Multi-Factor Authentication**: Require MFA for sensitive roles

## Support and Questions

For issues or questions about RBAC implementation:
1. Check [docs/user-roles-permissions.md](../docs/user-roles-permissions.md)
2. Review the permission functions in [accounts/permissions.py](../../accounts/permissions.py)
3. Examine example implementations in specific app views
